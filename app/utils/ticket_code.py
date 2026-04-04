from datetime import datetime
from secrets import randbelow

def generate_ticket_code() -> str:
    """
    Contoh Hasil :
    TCK-20260427-1234
    """
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = f"{randbelow(1_000_000):06d}"  # Generate Angka Acak 6 Digit
    return f"TCK-{date_part}-{random_part}"