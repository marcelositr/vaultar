import click
import os
import sys
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
import signal

from vaultar.config import get_default, DEFAULT_CONFIG_PATH
from vaultar.logger import log_event
from vaultar.core.validation import validate_sources, validate_destination, validate_backup_not_overwrite
from vaultar.core.backup import compress_files, encrypt_file
from vaultar.core.restore import decrypt_file, extract_files
from vaultar.ui.progress import create_progress

console = Console()

def handle_ctrl_c(sig, frame):
    console.print("\n[red]Process aborted by user.[/red]")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_ctrl_c)

@click.command()
@click.argument('sources', nargs=-1, type=click.Path(exists=False))
@click.option('-d', '--destino', help='Pasta de destino do backup')
@click.option('-c', '--compress', type=click.Choice(['tar', 'tar.gz', 'tar.zst', 'zip']), help='Tipo de compressão')
@click.option('-e', '--encrypt', type=click.Choice(['senha', 'chave']), help='Método de criptografia')
@click.option('-v', '--verbose', is_flag=True, help='Verbose detalhado')
@click.option('--restore', type=click.Path(exists=True), help='Restaura backup')
@click.option('--config', type=click.Path(exists=True), help='Arquivo de configuração opcional')
def main(sources, destino, compress, encrypt, verbose, restore, config):
    """Vaultar - Secure Backup & Restore Tool"""
    
    if restore:
        handle_restore(restore, verbose)
        return

    # Interactive flow if parameters are missing
    if not sources:
        sources_str = Prompt.ask("Informe arquivos/pastas (ex: ~/Documentos ~/teste.txt)")
        sources = sources_str.split()
    
    if not destino:
        default_dest = get_default("destination")
        destino = Prompt.ask("Informe destino do backup", default=default_dest if default_dest else ".")
    
    if not compress:
        default_compress = get_default("compression", "tar.gz")
        compress = Prompt.ask("Tipo de compressão", choices=['tar', 'tar.gz', 'tar.zst', 'zip'], default=default_compress)
    
    if not encrypt:
        default_encrypt = get_default("encryption_method", "senha")
        encrypt = Prompt.ask("Criptografia", choices=['senha', 'chave'], default=default_encrypt)

    if not verbose and get_default("verbose", "N").upper() == "N":
        verbose = Confirm.ask("Ativar verbose?", default=False, choices=["s", "n"], show_choices=True)
    else:
        verbose = True

    # Pre-action validation
    invalid_paths = validate_sources(sources)
    if invalid_paths:
        console.print(f"[red]Erro: Os seguintes caminhos não existem: {', '.join(invalid_paths)}[/red]")
        return

    dest_ok, dest_msg = validate_destination(destino)
    if not dest_ok:
        console.print(f"[red]Erro: {dest_msg}[/red]")
        return

    # Passphrase handling if needed
    passphrase = None
    recipient = None
    if encrypt == "senha":
        passphrase = Prompt.ask("Informe a senha do backup", password=True)
        confirm_pass = Prompt.ask("Confirme a senha", password=True)
        if passphrase != confirm_pass:
            console.print("[red]Erro: As senhas não conferem.[/red]")
            return
    elif encrypt == "chave":
        recipient = Prompt.ask("Informe o ID/email da chave GPG")

    # Summary
    show_summary(sources, destino, compress, encrypt, verbose)
    
    if not Confirm.ask("Existem regras e condições adicionais. Confirmar para prosseguir?", choices=["s", "n"]):
        console.print("[yellow]Operação cancelada.[/yellow]")
        return

    # Execution
    try:
        timestamp = datetime.now().strftime("%Y%m%d")
        base_name = f"{timestamp}-backup.{compress}"
        final_dest = Path(destino) / base_name
        
        with create_progress() as progress:
            task = progress.add_task("[cyan]Realizando backup...", total=100)
            
            # Step 1: Compress
            progress.update(task, description="Comprimindo arquivos...", advance=20)
            compress_files(sources, final_dest, compress)
            
            # Step 2: Encrypt
            progress.update(task, description="Criptografando...", advance=40)
            encrypted_file = encrypt_file(final_dest, encrypt, recipient, passphrase)
            
            # Step 3: Cleanup unencrypted
            progress.update(task, description="Finalizando...", advance=30)
            final_dest.unlink()
            
            progress.update(task, description="Concluído!", advance=10)

        console.print(f"[green]Backup concluído com sucesso: {encrypted_file}[/green]")
        log_event("BACKUP", {
            "sources": [str(s) for s in sources],
            "destination": str(encrypted_file),
            "compression": compress,
            "encryption": encrypt,
            "status": "success"
        })

    except Exception as e:
        console.print(f"[red]Erro durante o backup: {str(e)}[/red]")
        log_event("BACKUP_ERROR", {"error": str(e)})

def handle_restore(restore_file, verbose):
    """Handles the restore process."""
    console.print(f"[cyan]Restaurando backup: {restore_file}[/cyan]")
    
    passphrase = None
    # We don't know if it's password or key, but GPG will ask or we can prompt if symmetric
    # For simplicity, let's ask for passphrase if it's symmetric, but python-gnupg usually handles it.
    # However, the blueprint says "pergunta senha" in some contexts.
    passphrase = Prompt.ask("Informe a senha para descriptografar (se necessário)", password=True, default="")

    try:
        with create_progress() as progress:
            task = progress.add_task("[cyan]Restaurando...", total=100)
            
            # Decrypt
            progress.update(task, description="Descriptografando...", advance=40)
            decrypted_file = decrypt_file(restore_file, passphrase)
            
            # Determine compression type from filename
            # YYYYMMDD-backup.<compress>.gpg
            filename = Path(restore_file).name
            parts = filename.split('.')
            if len(parts) < 3:
                # Fallback or error
                compress_type = "tar.gz" # Default
            else:
                compress_type = parts[-2]
            
            # Extract
            progress.update(task, description="Extraindo arquivos...", advance=50)
            
            def overwrite_callback(path):
                return Confirm.ask(f"O arquivo {path} já existe. Sobrescrever?", default=False, choices=["s", "n"])
            
            extract_files(decrypted_file, compress_type, overwrite_callback)
            
            # Cleanup decrypted
            decrypted_file.unlink()
            progress.update(task, description="Concluído!", advance=10)

        console.print("[green]Restauração concluída com sucesso![/green]")
        log_event("RESTORE", {
            "file": str(restore_file),
            "status": "success"
        })

    except Exception as e:
        console.print(f"[red]Erro durante a restauração: {str(e)}[/red]")
        log_event("RESTORE_ERROR", {"error": str(e)})

def show_summary(sources, destino, compress, encrypt, verbose):
    table = Table(title="Resumo do Backup")
    table.add_column("Parâmetro", style="cyan")
    table.add_column("Valor", style="magenta")
    
    table.add_row("Arquivos/Pastas", ", ".join(sources))
    table.add_row("Destino", destino)
    table.add_row("Compressão", compress)
    table.add_row("Criptografia", encrypt)
    table.add_row("Verbose", "Sim" if verbose else "Não")
    
    console.print(table)

if __name__ == "__main__":
    main()
