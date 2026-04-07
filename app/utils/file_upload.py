from fastapi import HTTPException, UploadFile, status

def get_file_size(file: UploadFile) -> int:
    current_position = file.file.tell()
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(current_position)
    return size

def reset_file_pointer(file: UploadFile) -> None:
    file.file.seek(0)

def validate_image_file(file: UploadFile, max_size_mb: int) -> int:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File bukan gambar")
    
    size = get_file_size(file)
    if size > max_size_mb * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ukuran Gambar Maksimal {max_size_mb} MB.")
    
    reset_file_pointer(file)
    return size

def validate_video_file(file: UploadFile, max_size_mb: int) -> int:
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File bukan video")
    
    size = get_file_size(file)
    if size > max_size_mb * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ukuran Video Maksimal {max_size_mb} MB.")
    
    reset_file_pointer(file)
    return size