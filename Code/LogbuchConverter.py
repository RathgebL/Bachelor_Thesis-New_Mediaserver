import re, unicodedata, pandas as pd
from tkinter import Tk, filedialog
from pathlib import Path

# --- Utilities ---

def nfc(s: str) -> str:  # Unicode normalization
    return unicodedata.normalize("NFC", s or "")

def norm_name(s: str) -> str:  # Normalize person names
    s = nfc(s)
    s = s.replace("_", " ")
    s = re.sub(r",\s*(\S)", r", \1", s)  # enforce space after comma
    return s.strip()

def norm_text(s: str) -> str:  # Normalize general text (titles, albums, etc.)
    s = nfc(s)
    # s = s.replace("_", " ")
    # s = s.replace("--", "—")
    s = re.sub(r"\b[oO][pP]\.?\s*", "op. ", s)
    s = s.replace("Nº", "No")
    s = re.sub(r"\b(?:no|nr)\.?\s*(\d+)(?=\D|$)", r"Nr. \1", s, flags=re.IGNORECASE)
    return s.strip()

def natural_sort_key(s: str):
    # Split string into numeric and non-numeric parts for natural sorting
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s or "")]

# --- Data parsing ---

def parse_column_b(value):
    # Parse column B into Composer, Mediatitle, Interpreter(s).
    if pd.isna(value):
        return "", "", ""

    # Normalize dash variants with flexible spacing
    parts = re.split(r"\s*[-–]\s*", value)

    composer, mediatitle, interpreters = "", "", ""

    if len(parts) == 1:
        # No dash at all
        composer = parts[0]

    elif len(parts) == 2:
        # Normal case: Composer – Rest
        composer = norm_name(parts[0])
        rest = parts[1]

        # Split at last ". " if available
        if ". " in rest:
            last_dot = rest.rfind(". ")
            mediatitle = rest[:last_dot]
            interpreters = rest[last_dot + 2 :]
        else:
            mediatitle = rest

    else:
        # Special case: Composer – Mediatitle – Interpreters
        composer = parts[0]
        mediatitle = " – ".join(parts[1:-1])  # in case there are >2 dashes
        interpreters = parts[-1]

    return norm_name(composer), norm_text(mediatitle), norm_name(interpreters)

def convert_date(date_series):
    # Convert dd.mm.yy to yyyy-mm-dd, forward-fill missing values
    def fix_date(d):
        if pd.isna(d):
            return pd.NaT
        return pd.to_datetime(d, format="%d.%m.%y", errors="coerce")
    converted = date_series.apply(fix_date)
    return converted.ffill().dt.strftime("%Y-%m-%d")

def load_and_transform(file_path):
    df = pd.read_excel(file_path)

    results = []
    for _, row in df.iterrows():
        cd_number = str(row.iloc[0]).strip()
        composer, mediatitle, interpreters = parse_column_b(row.iloc[1])
        comment = norm_text(str(row.iloc[4])) if len(row) > 4 else ""
        date = row.iloc[5] if len(row) > 5 else None

        results.append({
            "CD Number": cd_number,
            "Composer": composer,
            "Mediatitle": mediatitle,
            "Interpreter": interpreters,
            "Place": "",
            "Status": "",
            "Date": date,
            "Comment": comment
        })

    df_out = pd.DataFrame(results)
    df_out["Date"] = convert_date(df_out["Date"])
    return df_out

# --- Main script ---

def main():
    Tk().withdraw()  # Hide root window
    file = filedialog.askopenfilename(
        title="Select your Excel file", filetypes=[("Excel files", "*.xlsx *.xls *.ods")]
    )
    if not file:
        print("No file selected.")
        return

    df = load_and_transform(file)

    # Natural sort by CD Number
    df = df.sort_values(by="CD Number", key=lambda col: col.map(natural_sort_key))

    output_path = Path(file).with_name("converted_output.xlsx")
    df.to_excel(output_path, index=False)
    print(f"Converted file saved as {output_path}")

if __name__ == "__main__":
    main()
