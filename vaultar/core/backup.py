import os
import tarfile
import zipfile
import zstandard as zstd
from pathlib import Path
from datetime import datetime
import gnupg
import shutil

def compress_files(sources, dest_file, compress_type):
    """Compresses files based on the specified type."""
    sources = [Path(s).expanduser().resolve() for s in sources]
    dest_file = Path(dest_file).expanduser().resolve()
    
    if compress_type == "zip":
        with zipfile.ZipFile(dest_file, "w", zipfile.ZIP_DEFLATED) as zipf:
            for source in sources:
                if source.is_dir():
                    for root, dirs, files in os.walk(source):
                        for file in files:
                            file_path = Path(root) / file
                            # Use absolute path internally as requested by blueprint
                            zipf.write(file_path, file_path)
                else:
                    zipf.write(source, source)
                    
    elif compress_type in ["tar", "tar.gz", "tar.zst"]:
        mode = "w"
        if compress_type == "tar.gz":
            mode = "w:gz"
        
        if compress_type == "tar.zst":
            # Manual zstd handling if not supported natively by tarfile
            temp_tar = dest_file.with_suffix(".tar")
            with tarfile.open(temp_tar, "w") as tar:
                for source in sources:
                    tar.add(source, source)
            
            cctx = zstd.ZstdCompressor()
            with open(temp_tar, "rb") as f_in:
                with open(dest_file, "wb") as f_out:
                    cctx.copy_stream(f_in, f_out)
            temp_tar.unlink()
        else:
            with tarfile.open(dest_file, mode) as tar:
                for source in sources:
                    tar.add(source, source)
    else:
        raise ValueError(f"Unsupported compression type: {compress_type}")

def encrypt_file(input_file, encrypt_method, recipient=None, passphrase=None):
    """Encrypts the file using GPG."""
    gpg = gnupg.GPG()
    input_file = Path(input_file).expanduser().resolve()
    output_file = Path(str(input_file) + ".gpg")
    
    with open(input_file, "rb") as f:
        if encrypt_method == "senha":
            status = gpg.encrypt_file(f, recipients=None, symmetric=True, passphrase=passphrase, output=str(output_file))
        else:
            status = gpg.encrypt_file(f, recipients=[recipient], output=str(output_file))
            
    if not status.ok:
        raise Exception(f"Encryption failed: {status.stderr}")
        
    return output_file
