# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields

class AccountInvoice(models.Model):
    _inherit = "account.move"

    text_message = fields.Text("Message")
