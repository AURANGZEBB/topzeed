# -*- coding: utf-8 -*-
#################################################################################
# Author      : CFIS (<https://www.cfis.store/>)
# Copyright(c): 2017-Present CFIS.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://www.cfis.store/>
#################################################################################

{
    "name": "Parent Account / Chart of Accounts Hierarchy / Chart of Account Hierarchy / Account Hierarchy",
    "summary": "The hierarchy of accounts defines how accounts are related to one another. This module will visually add the parent id of each account and build a tree structure relationship between accounts.",
    "version": "15.0.1",
    "description": """
        The hierarchy of accounts defines how accounts are related to one another. 
        This module will visually add the parent id of each account and build a tree structure relationship between accounts. 
        Parent Account.
        Chart of Accounts Hierarchy.
        Chart of Account Hierarchy.
        Account Hierarchy.
        Parent Hierarchy.
    """,    
    "author": "CFIS",
    "maintainer": "CFIS",
    "license" :  "Other proprietary",
    "website": "https://www.cfis.store",
    "images": ["images/odoo_account_hierarchy.png"],
    "category": "Accounting Management",
    "depends": [
        "account",
    ],
    "data": [
        "security/account_hierarchy_security.xml",
        "security/ir.model.access.csv",
        "data/account_hierarchy_data.xml",
        "views/template.xml",
        "views/account_account_views.xml",
        "report/report_template.xml",
        "report/report.xml",
        "wizard/account_hierarchy_view.xml",        
    ],
    "assets": {
        "web.assets_backend": [
            "/odoo_account_hierarchy/static/src/css/style.css",
            "/odoo_account_hierarchy/static/src/css/report.css",            
            "/odoo_account_hierarchy/static/src/js/account_hierarchy_backend.js",
            "/odoo_account_hierarchy/static/src/js/account_hierarchy_widgets.js",
        ],
        "web.report_assets_common": [
            "/odoo_account_hierarchy/static/src/css/report.css",
        ],
        "web.assets_qweb": [
            "/odoo_account_hierarchy/static/src/xml/*.xml",
        ],
    },
    "installable": True,
    "application": True,
    "price"                :  12,
    "currency"             :  "EUR",
    "pre_init_hook"        :  "pre_init_check", 
}
