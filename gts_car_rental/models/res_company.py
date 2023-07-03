from  odoo import fields,models


class ResCompany(models.Model):
    _inherit = 'res.company'

    default_amount = fields.Float('Default Security Deposit Amount',)