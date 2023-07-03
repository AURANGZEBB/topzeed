# -*- coding: utf-8 -*-
{
    'name': 'Rental CAR Business  Solution FOR Saudi And Middle East|Gts Car Rental|Fleet Rental|vehicle on rent',
    'version': '15.0.2.1.0',
    'summary': 'Fleet',
    'sequence': -100,
    'description': """carrental,car rental,car,rental buisness,car on rent,rent on car,carrent,rentcar,car,rent,
    odoo car rent,odoo car rental,rented car,rental car buisness,car rent,car,rent,odoo car,odoo rental ,odoorental
    buisness,rent business, buisness for rent,car rent,rentcar,odoo car rent,carrent 14,odoo 14 car rent,odoo14carrent,odoocarrent,
    14carrent,14 car rent,rent car,car,rentcar,car,rentcar,rent car,car rent,odoo rent,odoorent,odoocar, 
    odoo car,odoo rent,rent car,carrent,rentcar,carrent,car,odoorentalcar,rentcar,odoorentcar,rentcar14,odoorentcar,
    odoocar,odoo14car,rent14,carrent""",
    'category': '',
    'author': 'Geotechnosoft',
    'maintainer': 'Geotechnosoft',
    'license': 'AGPL-3',
    'depends': [
        'sale','sale_management','fleet','base','contacts','account'


    ],
    'data': ['security/ir.model.access.csv',
             'security/groups.xml',
             'views/res_company_view.xml',
             'views/res_partner_view.xml',
             'views/report_payment_receipt_templates.xml',
             'views/car_rental_report_template.xml',
            'views/sale_order_view.xml',
             'views/fleet_view.xml',
             'views/sale_order_report_view.xml',
             'views/product_view.xml',
             'wizard/document_attachment_view.xml',
             'wizard/receive_money_view.xml',
             'wizard/send_money_view.xml',
             'wizard/due_amount_view.xml',
             'wizard/tamm_autho_view.xml',
             'data/scheduler_cron.xml',
             'data/scheduler_car_rental_cron.xml',

    ],
    'images': ['static/description/banner.png'],
    'price': 99.56,
    'currency': 'USD',
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'application': True,
    'installable': True,
}
