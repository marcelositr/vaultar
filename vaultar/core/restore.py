import os
import tarfile
import zipfile
import zstandard as zstd
from pathlib import Path
import gnupg
import shutil

def decrypt_file(input_file, passphrase=None):
    """Decrypts the file using GPG."""
    gpg = gnupg.GPG()
    input_file = Path(input_file).expanduser().resolve()
    # Remove .gpg extension for output
    output_file = Path(str(input_file).replace(".gpg", ""))
    
    with open(input_file, "rb") as f:
        status = gpg.decrypt_file(f, passphrase=passphrase, output=str(output_file))
        
    if not status.ok:
        raise Exception(f"Decryption failed: {status.stderr}")
        
    return output_file

def extract_files(archive_file, compress_type, overwrite_callback=None):
    """Extracts files from the archive, respecting absolute paths."""
    archive_file = Path(archive_file).expanduser().resolve()
    
    if compress_type == "zip":
        with zipfile.ZipFile(archive_file, "r") as zipf:
            for member in zipf.infolist():
                dest_path = Path(member.filename)
                if dest_path.exists() and overwrite_callback:
                    if not overwrite_callback(dest_path):
                        continue
                zipf.extract(member, "/")
                
    elif compress_type in ["tar", "tar.gz", "tar.zst"]:
        if compress_type == "tar.zst":
            # Decompress zst first
            temp_tar = archive_file.with_suffix(".tar")
            dctx = zstd.ZstdDecompressor()
            with open(archive_file, "rb") as f_in:
                with open(temp_tar, "wb") as f_out:
                    dctx.copy_stream(f_in, f_out)
            
            with tarfile.open(temp_tar, "r") as tar:
                for member in tar.getmembers():
                    dest_path = Path(member.name)
                    if dest_path.exists() and overwrite_callback:
                        if not overwrite_callback(dest_path):
                            continue
                    tar.extract(member, "/")
            temp_tar.unlink()
        else:
            mode = "r"
            if compress_type == "tar.gz":
                mode = "r:gz"
            with tarfile.open(archive_file, mode) as tar:
                for member in tar.getmembers():
                    dest_path = Path(member.name)
                    if dest_path.exists() and overwrite_callback:
                        if not overwrite_callback(dest_path):
                            continue
                    tar.extract(member, "/")
    else:
        raise ValueError(f"Unsupported compression type: {compress_type}")
