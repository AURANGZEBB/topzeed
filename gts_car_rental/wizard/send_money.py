# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _name = 'account.deposit.payment'
    _description = 'Deposit Payment'

    # == Business fields ==
    payment_date = fields.Date(string="Payment Date", required=True,
        default=fields.Date.context_today)
    amount = fields.Monetary(currency_field='currency_id', store=True, readonly=False,
         compute='_compute_amount')
    communication = fields.Char(string="Memo", store=True, readonly=False,
        compute='_compute_communication')
    currency_id = fields.Many2one('res.currency', string='Currency', store=True, readonly=False,
        related='company_id.currency_id',
        help="The payment's currency.")
    journal_id = fields.Many2one('account.journal', store=True, readonly=False,
        compute='_compute_journal_id',
        domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]")
    partner_bank_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account",
        readonly=False, store=True,
        compute='_compute_partner_bank_id',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('partner_id', '=', partner_id)]")
    company_currency_id = fields.Many2one('res.currency', string="Company Currency",
        related='company_id.currency_id')

    # == Fields given through the context ==
    payment_type = fields.Selection([
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),
    ], string='Payment Type', store=True, copy=False,
        compute='_compute_from_lines')
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
    ], store=True, copy=False,
        compute='_compute_from_lines')
    company_id = fields.Many2one('res.company', store=True, copy=False,
        )
    partner_id = fields.Many2one('res.partner',
        string="Customer/Vendor", store=True, copy=False, ondelete='restrict',
        )

    @api.depends('company_id')
    def _compute_journal_id(self):
        for wizard in self:
            domain = [
                ('type', 'in', ('bank', 'cash')),
                ('company_id', '=', wizard.company_id.id),
            ]
            journal = None
            if not journal:
                journal = self.env['account.journal'].search(domain, limit=1)
            wizard.journal_id = journal


    @api.depends('partner_id')
    def _compute_partner_bank_id(self):
        ''' The default partner_bank_id will be the first available on the partner. '''
        for wizard in self:
            available_partner_bank_accounts = wizard.partner_id.bank_ids.filtered(
                lambda x: x.company_id in (False, wizard.company_id))
            if available_partner_bank_accounts:
                wizard.partner_bank_id = available_partner_bank_accounts[0]._origin
            else:
                wizard.partner_bank_id = False

    @api.depends('payment_date','partner_id','journal_id')
    def _compute_amount(self):
        sale_id = self.env['sale.order'].browse(self.env.context.get('active_id'))
        for wizard in self:
            if sale_id.returning_amount:
                wizard.amount = sale_id.returning_amount

    @api.depends('payment_date', 'partner_id', 'journal_id')
    def _compute_communication(self):
        sale_id = self.env['sale.order'].browse(self.env.context.get('active_id'))
        for wizard in self:
            if sale_id.state == 'sale' or 'lock':
                wizard.communication = sale_id.name

    def action_create_payments(self):
        sale_id = self.env['sale.order'].browse(self.env.context.get('active_id'))
        vals = {
            'payment_type': self.payment_type,
            'partner_type' : self.partner_type,
            'partner_id' : self.partner_id.id,
            'company_id' : self.company_id.id,
            'amount' : self.amount,
            'date' : self.payment_date,
            'ref' : self.communication,
            'journal_id' : self.journal_id.id,
            'partner_bank_id' : self.partner_bank_id.id,
            'sale_id' : sale_id.id
        }
        payment = self.env['account.payment'].create(vals)
        payment.action_post()
