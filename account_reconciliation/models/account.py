# -*- coding: utf-8 -*-
# Code of Odoo Developers. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountAccount(models.Model):
    _inherit = "account.account"

    def action_open_reconcile(self):
        self.ensure_one()
        action_context = {'show_mode_selector': False, 'mode': 'accounts', 'account_ids': [self.id,]}
        return {
            'type': 'ir.actions.client',
            'tag': 'manual_reconciliation_view',
            'context': action_context,
        }
