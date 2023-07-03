# -*- coding: utf-8 -*-
{
    'name': 'WhatsApp Payments Integration',
    'version': '15.0.1.0.0',
    'category': 'Tools',
    'author': 'InTechual Solutions',
    'license': 'OPL-1',
    'summary': 'WhatsApp/Payments Integration',
    'description': """
This module can be used to send Payment Receipts via WhatsApp
----------------------------------------------------------

Send Payment Receipts via WhatsApp
""",
    'depends': ['base', 'account', 'whatsapp_integration'],
    'data': [
        'views/account_payment_form_wa_inherited.xml',
    ],
    'external_dependencies': {'python': ['phonenumbers', 'selenium']},
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    'currency': 'EUR',
    'price': 10,
}
