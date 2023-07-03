# -*- coding: utf-8 -*-
# Code of Odoo Developers. See LICENSE file for full copyright and licensing details.

{
    'name': 'Reconciliation Widget For Odoo 15',
    'version': '15.0.3.0.0',
    'category': 'Accounting',
    'summary': 'Reconcile Customer Invoice, Vendor Bills and Bank Statements',
    'description': 'Reconcile Customer Invoice, Vendor Bills and Bank Statements',
    'sequence': '1',
    'author': 'Odoo SA, Odoo Developers',
    'support': 'developersodoo@gmail.com',
    'live_test_url': 'https://www.youtube.com/watch?v=QWIUSu3D2sE',
    'depends': ['account'],
    'demo': [],
    'data': [
        'views/account_view.xml',
        'views/account_bank_statement_view.xml',
        'views/account_journal_dashboard_view.xml',
        'views/account_payment_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_reconciliation/static/src/scss/account_reconciliation.scss',
            'account_reconciliation/static/src/js/reconciliation_action.js',
            'account_reconciliation/static/src/js/reconciliation_model.js',
            'account_reconciliation/static/src/js/reconciliation_renderer.js',
        ],
         'web.assets_qweb': [
            "account_reconciliation/static/src/xml/account_reconciliation.xml",
        ],
    },
    'license': 'OPL-1',
    'price': 45,
    'currency': 'USD',
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.gif'],
}
