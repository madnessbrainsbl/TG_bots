#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '/app')
from utils.file_utils import generate_files

ctx={
 'fio':'тест', 'rodfio':'тест род', 'krfio':'тест кр', 'music_fio':'мавтор', 'text_fio':'тавтор',
 'fonog_fio':'изготов', 'track':'трек', 'passport':'паспорт', 'pseudonym':'псевдо',
 'works':[
   {'title':'A','music_fio':'M1','text_fio':'T1','pseudonym':'P1','fonog_fio':'F1','author_rights':'100%','neighboring_rights':'100%','year':'2024'},
   {'title':'B','music_fio':'M2','text_fio':'T2','pseudonym':'P2','fonog_fio':'F2','author_rights':'50%','neighboring_rights':'50%','year':'2025'}
 ]
}

docx, pdf = generate_files('add_agreement_OOO', ctx)
print('DOCX:', docx)
print('PDF :', pdf)

