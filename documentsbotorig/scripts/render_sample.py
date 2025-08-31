from pathlib import Path
import sys

# Ensure project root is on sys.path when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.file_utils import generate_files

BASE = Path(__file__).resolve().parents[1]
TPL_DIR = BASE / "templates" / "add_agreement_OOO"

context = {
    "pseudonym": "DJ Test",
    "rodfio": "Иванова Ивана Ивановича",
    "works": [
        {
            "title": "Трек 1",
            "music_fio": "Автор Музыки 1",
            "text_fio": "Автор Текста 1",
            "pseudonym": "Исполнитель 1",
            "fonog_fio": "Изготовитель 1",
            "author_rights": "исключительное право на воспроизведение",
            "neighboring_rights": "право на доведение до всеобщего сведения",
            "year": "2023",
        },
        {
            "title": "Трек 2",
            "music_fio": "Автор Музыки 2",
            "text_fio": "Автор Текста 2",
            "pseudonym": "Исполнитель 2",
            "fonog_fio": "Изготовитель 2",
            "author_rights": "право на распространение",
            "neighboring_rights": "право на прокат",
            "year": "2024",
        },
        {
            "title": "Трек 3",
            "music_fio": "Автор Музыки 3",
            "text_fio": "Автор Текста 3",
            "pseudonym": "Исполнитель 3",
            "fonog_fio": "Изготовитель 3",
            "author_rights": "право на импорт",
            "neighboring_rights": "право на сообщение в эфир",
            "year": "2025",
        },
    ],
}

docx_path, pdf_path = generate_files("add_agreement_OOO", context, output_dir=str(TPL_DIR))
print("DOCX:", docx_path)
print("PDF:", pdf_path)
