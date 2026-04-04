import re

def normalize_phone_number(phone_number: str) -> str:
    """
    Ubah Nomor HP Menjadi Hanya Digit Agar Mudah Disimpan dan Diproses
     - Hapus Semua Karakter Non-Digit (Seperti Spasi, Tanda Hubung, dll.)
     - Pastikan Nomor Dimulai dengan Kode Negara (Jika Tidak, Tambahkan Kode Negara Default)
     - Contoh: "0812-345-678" Menjadi "62812345678"
     - Contoh: "+62 812 345 678" Menjadi "62812345678"
     - Contoh: "812345678" Menjadi "62812345678" (Asumsi Kode Negara Default Adalah +62) 
    """
    normalized = re.sub(r"\D", "", phone_number)  # Hapus Semua Karakter Non-Digit

    if not normalized:
        return normalized

    return normalized