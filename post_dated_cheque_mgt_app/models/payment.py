# -*- coding: utf-8 -*-

import math
from datetime import date, datetime
from odoo import models, fields, api, _
from odoo.tools import float_round, float_is_zero
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

MAP_INVOICE_TYPE_PARTNER_TYPE = {
	'out_invoice': 'customer',
	'out_refund': 'customer',
	'out_receipt': 'customer',
	'in_invoice': 'supplier',
	'in_refund': 'supplier',
	'in_receipt': 'supplier',
}


class AccountMove(models.Model):
	_inherit = "account.move"

	def action_invoice_pdc_register_payment(self):
		return self.env['pdc.account.payment']\
			.with_context(active_ids=self.ids, active_model='account.move', active_id=self.id)\
			.action_register_payment()


class AccountMoveLine(models.Model):
	_inherit = "account.move.line"
	
	payment_pdc_id = fields.Many2one('pdc.account.payment', string="Originator PDC Payment", help="Payment that created this entry", copy=False)


class PdcAccountPayment(models.Model):
	_name = "pdc.account.payment"
	# _inherits = {'account.move': 'account_move_id'}
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Payments"
	_order = "payment_date desc, name desc"


	name = fields.Char(readonly=True, copy=False)  # The name is attributed upon post()
	payment_reference = fields.Char(copy=False, readonly=True, help="Reference of the document used to issue this payment. Eg. check number, file name, etc.")
	move_name = fields.Char(string='Journal Entry Name', readonly=True,
		default=False, copy=False,
		help="Technical field holding the number given to the journal entry, automatically set when the statement line is reconciled then stored to set the same number again if the line is cancelled, set to draft and re-processed again.")

	# Money flows from the journal_id's payment_debit_account_id or payment_credit_account_id to the destination_account_id
	destination_account_id = fields.Many2one('account.account', compute='_compute_destination_account_id', readonly=True)
	# For money transfer, money goes from journal_id to a transfer account, then from the transfer account to destination_journal_id
	destination_journal_id = fields.Many2one('account.journal', string='Transfer To', domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]", readonly=True, states={'draft': [('readonly', False)]})

	invoice_ids = fields.Many2many('account.move', help="""Technical field containing the invoices for which the payment has been generated.This does not especially correspond to the invoices reconciled with the payment,as it can have been generated first, and reconciled later""")
	move_line_ids = fields.One2many('account.move.line', 'payment_pdc_id', readonly=True, copy=False)

	state = fields.Selection([('draft', 'Draft'),
							('collect_cash','Collect Cash'),
							('deposited', 'Deposited'),
							('bounced', 'Bounced'),
							('posted', 'Posted'),
							('returned', 'Returned'),
							('cancelled', 'Cancelled'),
							], readonly=True, default='draft', copy=False, string="Status")

	is_internal_transfer = fields.Boolean(string="Internal Transfer",
		readonly=False, store=True,
		tracking=True,
		compute="_compute_is_internal_transfer")

	payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money'), ('transfer', 'Internal Transfer')], string='Payment Type', required=True, readonly=True, states={'draft': [('readonly', False)]})

	partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')], tracking=True, readonly=True, states={'draft': [('readonly', False)]})
	partner_id = fields.Many2one('res.partner', string='Partner', tracking=True, readonly=True, states={'draft': [('readonly', False)]}, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

	amount = fields.Monetary(string='Amount', required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
	currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company.currency_id)
	payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, readonly=True, states={'draft': [('readonly', False)]}, copy=False, tracking=True)
	communication = fields.Char(string='Memo', readonly=True, states={'draft': [('readonly', False)]})
	journal_id = fields.Many2one('account.journal', store=True, readonly=False,
		compute='_compute_journal_id',
		domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]")
	company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
		default=lambda self: self.env.company)


	# == Payment methods fields ==
	available_payment_method_line_ids = fields.Many2many('account.payment.method.line',
		compute='_compute_payment_method_line_fields')
	payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
		readonly=False, store=True,
		compute='_compute_payment_method_line_id',
		domain="[('id', 'in', available_payment_method_line_ids)]",
		help="Manual: Pay or Get paid by any method outside of Odoo.\n"
		"Payment Acquirers: Each payment acquirer has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
		"Check: Pay bills by check and print it from Odoo.\n"
		"Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
		"SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
		"SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n")
	hide_payment_method_line = fields.Boolean(
		compute='_compute_payment_method_line_fields',
		help="Technical field used to hide the payment method if the selected journal has only one available which is 'manual'")
	payment_method_id = fields.Many2one(
		related='payment_method_line_id.payment_method_id',
		string="Method",
		tracking=True,
		store=True
	)
	payment_method_code = fields.Char(related='payment_method_id.code',
		help="Technical field used to adapt the interface to the payment type selected.", readonly=True)
	hide_payment_method = fields.Boolean(compute='_compute_hide_payment_method',
										 help="Technical field used to hide the payment method if the "
										 "selected journal has only one available which is 'manual'")

	payment_difference = fields.Monetary(compute='_compute_payment_difference', readonly=True)
	payment_difference_handling = fields.Selection([('open', 'Keep open'), ('reconcile', 'Mark invoice as fully paid')], default='open', string="Payment Difference Handling", copy=False)
	writeoff_account_id = fields.Many2one('account.account', string="Difference Account", domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", copy=False)
	writeoff_label = fields.Char(
		string='Journal Item Label',
		help='Change label of the counterpart that will hold the payment difference',
		default='Write-Off')
	partner_bank_account_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account", readonly=True, states={'draft': [('readonly', False)]}, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
	show_partner_bank_account = fields.Boolean(compute='_compute_show_partner_bank', help='Technical field used to know whether the field `partner_bank_account_id` needs to be displayed or not in the payments form views')
	require_partner_bank_account = fields.Boolean(compute='_compute_show_partner_bank', help='Technical field used to know whether the field `partner_bank_account_id` needs to be required or not in the payments form views')
	bank = fields.Char(string='Bank')
	agent = fields.Char(string='Agent')
	cheque_reference = fields.Char(string='Cheque Reference')
	due_date = fields.Date(string='Due Date', required=True, copy=False)
	account_move_id = fields.Many2one('account.move', string="Move Reference")
	pdc_account_id = fields.Many2one('account.account',string="PDC Receivable Account")
	pdc_account_creditors_id = fields.Many2one('account.account',string="PDC Payable Account")
	attachment_number = fields.Integer(compute='_compute_attachment_number', string='Number of Attachments')


	@api.depends('partner_id', 'journal_id', 'destination_journal_id')
	def _compute_is_internal_transfer(self):
		for payment in self:
			payment.is_internal_transfer = payment.partner_id \
										   and payment.partner_id == payment.journal_id.company_id.partner_id \
										   and payment.destination_journal_id

	@api.depends('company_id', 'move_line_ids')
	def _compute_journal_id(self):
		for wizard in self:
			if wizard.journal_id:
				wizard.journal_id = wizard.journal_id
			else:
				partner_bank_id = wizard.move_line_ids.move_id.mapped('partner_bank_id')
				company_domain = [('company_id', '=', wizard.company_id.id)]
				bank_domain = [('bank_account_id', '=', partner_bank_id.id), ('type', '=', 'bank')] if len(partner_bank_id) == 1 else None
				no_bank_domain = [('type', 'in', ('bank', 'cash'))]
				journal = None
				if not journal:
					journal = self.env['account.journal'].search(company_domain + no_bank_domain, limit=1)
				wizard.journal_id = journal

	def _compute_attachment_number(self):
		Attachment = self.env['ir.attachment']
		for payment in self:
			payment.attachment_number = Attachment.search_count([
				('res_model', '=', 'pdc.account.payment'), ('res_id', '=', payment.id),
			])

	def action_get_attachment_view(self):
		return True
	
	@api.onchange('due_date')
	def check_pdc_account(self):
		if self.due_date:
			pdc_account_id = self.company_id.pdc_account_id
			if not pdc_account_id:
				raise UserError(_("Please configure Pdc Payment Account(100501) first, from Invoicing or Accounting setting."))
			pdc_account_creditors_id = self.company_id.pdc_account_creditors_id
			if not pdc_account_creditors_id:
				raise UserError(_("Please configure Pdc Payment Account(100502) first, from Invoicing or Accounting setting."))
			if self.due_date < fields.Date.today():
				raise UserError(_("Please select valid due date...!"))

	@api.model
	def default_get(self, default_fields):
		rec = super(PdcAccountPayment, self).default_get(default_fields)
		active_ids = self._context.get('active_ids') or self._context.get('active_id')
		active_model = self._context.get('active_model')

		# Check for selected invoices ids
		if not active_ids or active_model != 'account.move':
			return rec

		invoices = self.env['account.move'].browse(active_ids).filtered(lambda move: move.is_invoice(include_receipts=True))

		# Check all invoices are open
		if not invoices or any(invoice.state != 'posted' for invoice in invoices):
			raise UserError(_("You can only register payments for open invoices"))
		# Check if, in batch payments, there are not negative invoices and positive invoices
		dtype = invoices[0].move_type
		for inv in invoices[1:]:
			if inv.move_type != dtype:
				if ((dtype == 'in_refund' and inv.move_type == 'in_invoice') or
						(dtype == 'in_invoice' and inv.move_type == 'in_refund')):
					raise UserError(_("You cannot register payments for vendor bills and supplier refunds at the same time."))
				if ((dtype == 'out_refund' and inv.move_type == 'out_invoice') or
						(dtype == 'out_invoice' and inv.move_type == 'out_refund')):
					raise UserError(_("You cannot register payments for customer invoices and credit notes at the same time."))

		amount = self._compute_payment_amount(invoices, invoices[0].currency_id, invoices[0].journal_id, rec.get('payment_date') or fields.Date.today())
		rec.update({
			'currency_id': invoices[0].currency_id.id,
			'amount': abs(amount),
			'payment_type': 'inbound' if amount > 0 else 'outbound',
			'partner_id': invoices[0].commercial_partner_id.id,
			'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type],
			'communication': invoices[0].payment_reference or invoices[0].ref or invoices[0].name,
			'invoice_ids': [(6, 0, invoices.ids)],
		})
		return rec

	@api.constrains('amount')
	def _check_amount(self):
		for payment in self:
			if payment.amount < 0:
				raise ValidationError(_('The payment amount cannot be negative.'))

	@api.model
	def _get_method_codes_using_bank_account(self):
		return []

	@api.model
	def _get_method_codes_needing_bank_account(self):
		return []

	@api.depends('payment_type', 'journal_id')
	def _compute_payment_method_line_id(self):
		''' Compute the 'payment_method_line_id' field.
		This field is not computed in '_compute_payment_method_fields' because it's a stored editable one.
		'''
		for pay in self:
			available_payment_method_lines = pay.journal_id._get_available_payment_method_lines(pay.payment_type)

			# Select the first available one by default.
			if pay.payment_method_line_id in available_payment_method_lines:
				pay.payment_method_line_id = pay.payment_method_line_id
			elif available_payment_method_lines:
				pay.payment_method_line_id = available_payment_method_lines[0]._origin
			else:
				pay.payment_method_line_id = False

	@api.depends('payment_type', 'journal_id')
	def _compute_payment_method_line_fields(self):
		for pay in self:
			pay.available_payment_method_line_ids = pay.journal_id._get_available_payment_method_lines(pay.payment_type)
			to_exclude = self._get_payment_method_codes_to_exclude()
			if to_exclude:
				pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(lambda x: x.code not in to_exclude)
			if pay.payment_method_line_id.id not in pay.available_payment_method_line_ids.ids:
				# In some cases, we could be linked to a payment method line that has been unlinked from the journal.
				# In such cases, we want to show it on the payment.
				pay.hide_payment_method_line = False
			else:
				pay.hide_payment_method_line = len(pay.available_payment_method_line_ids) == 1 and pay.available_payment_method_line_ids.code == 'manual'

	def _get_payment_method_codes_to_exclude(self):
		# can be overriden to exclude payment methods based on the payment characteristics
		self.ensure_one()
		return []

	@api.depends('payment_method_code')
	def _compute_show_partner_bank(self):
		""" Computes if the destination bank account must be displayed in the payment form view. By default, it
		won't be displayed but some modules might change that, depending on the payment type."""
		for payment in self:
			payment.show_partner_bank_account = payment.payment_method_code in self._get_method_codes_using_bank_account()
			payment.require_partner_bank_account = payment.state == 'draft' and payment.payment_method_code in self._get_method_codes_needing_bank_account()

	@api.depends('payment_type', 'journal_id')
	def _compute_hide_payment_method(self):
		for payment in self:
			if not payment.journal_id or payment.journal_id.type not in ['bank', 'cash']:
				payment.hide_payment_method = True
				continue
			journal_payment_methods = payment.payment_type == 'inbound'\
				and payment.journal_id.inbound_payment_method_ids\
				or payment.journal_id.outbound_payment_method_ids
			payment.hide_payment_method = len(journal_payment_methods) == 1 and journal_payment_methods[0].code == 'manual'

	@api.depends('invoice_ids', 'amount', 'payment_date', 'currency_id', 'payment_type')
	def _compute_payment_difference(self):
		draft_payments = self.filtered(lambda p: p.invoice_ids and p.state == 'draft')
		for pay in draft_payments:
			payment_amount = -pay.amount if pay.payment_type == 'outbound' else pay.amount
			pay.payment_difference = pay._compute_payment_amount(pay.invoice_ids, pay.currency_id, pay.journal_id, pay.payment_date) - payment_amount
		(self - draft_payments).payment_difference = 0

	@api.onchange('journal_id')
	def _onchange_journal(self):
		self.account_move_id._onchange_journal()


	@api.model
	def _compute_payment_amount(self, invoices, currency, journal, date):
		'''Compute the total amount for the payment wizard.

		:param invoices:    Invoices on which compute the total as an account.invoice recordset.
		:param currency:    The payment's currency as a res.currency record.
		:param journal:     The payment's journal as an account.journal record.
		:param date:        The payment's date as a datetime.date object.
		:return:            The total amount to pay the invoices.
		'''
		company = journal.company_id
		currency = currency or journal.currency_id or company.currency_id
		date = date or fields.Date.today()

		if not invoices:
			return 0.0

		self.env['account.move'].flush(['move_type', 'currency_id'])
		self.env['account.move.line'].flush(['amount_residual', 'amount_residual_currency', 'move_id', 'account_id'])
		self.env['account.account'].flush(['user_type_id'])
		self.env['account.account.type'].flush(['type'])
		self._cr.execute('''
			SELECT
				move.move_type AS type,
				move.currency_id AS currency_id,
				SUM(line.amount_residual) AS amount_residual,
				SUM(line.amount_residual_currency) AS residual_currency
			FROM account_move move
			LEFT JOIN account_move_line line ON line.move_id = move.id
			LEFT JOIN account_account account ON account.id = line.account_id
			LEFT JOIN account_account_type account_type ON account_type.id = account.user_type_id
			WHERE move.id IN %s
			AND account_type.type IN ('receivable', 'payable')
			GROUP BY move.id, move.move_type
		''', [tuple(invoices.ids)])
		query_res = self._cr.dictfetchall()

		total = 0.0
		for res in query_res:
			move_currency = self.env['res.currency'].browse(res['currency_id'])
			if move_currency == currency and move_currency != company.currency_id:
				total += res['residual_currency']
			else:
				total += company.currency_id._convert(res['amount_residual'], currency, company, date)
		return total

	def name_get(self):
		return [(payment.id, payment.name or _('Draft Payment')) for payment in self]

	@api.model
	def _get_move_name_transfer_separator(self):
		return '§§'

	@api.depends('journal_id', 'partner_id', 'partner_type')
	def _compute_destination_account_id(self):
		self.destination_account_id = False
		for pay in self:
			if pay.partner_type == 'customer':
				# Receive money from invoice or send money to refund it.
				if pay.partner_id:
					pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_receivable_id
				else:
					pay.destination_account_id = self.env['account.account'].search([
						('company_id', '=', pay.company_id.id),
						('internal_type', '=', 'receivable'),
						('deprecated', '=', False),
					], limit=1)
			elif pay.partner_type == 'supplier':
				# Send money to pay a bill or receive money to refund it.
				if pay.partner_id:
					pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_payable_id
				else:
					pay.destination_account_id = self.env['account.account'].search([
						('company_id', '=', pay.company_id.id),
						('internal_type', '=', 'payable'),
						('deprecated', '=', False),
					], limit=1)


	def action_register_payment(self):
		active_ids = self.env.context.get('active_ids')
		if not active_ids:
			return ''
		return {
			'name': _('PDC Payment'),
			'res_model': 'pdc.account.payment',
			'view_mode': 'form',
			'view_id': self.env.ref('post_dated_cheque_mgt_app.view_pdc_account_payment_invoice_form').id,
			'context': self.env.context,
			'target': 'new',
			'type': 'ir.actions.act_window',
		}

	def cancel(self):
		self.write({'state': 'cancelled'})

	def unlink(self):
		if any(bool(rec.move_line_ids) for rec in self):
			raise UserError(_("You cannot delete a payment that is already posted."))
		if any(rec.move_name for rec in self):
			raise UserError(_('It is not allowed to delete a payment that already created a journal entry since it would create a gap in the numbering. You should create the journal entry again and cancel it thanks to a regular revert.'))
		return super(PdcAccountPayment, self).unlink()

	def _prepare_payment_moves(self):
		''' Prepare the creation of journal entries (account.move) by creating a list of python dictionary to be passed
		to the 'create' method.

		Example 1: outbound with write-off:

		Account             | Debit     | Credit
		---------------------------------------------------------
		BANK                |   900.0   |
		RECEIVABLE          |           |   1000.0
		WRITE-OFF ACCOUNT   |   100.0   |

		Example 2: internal transfer from BANK to CASH:

		Account             | Debit     | Credit
		---------------------------------------------------------
		BANK                |           |   1000.0
		TRANSFER            |   1000.0  |
		CASH                |   1000.0  |
		TRANSFER            |           |   1000.0

		:return: A list of Python dictionary to be passed to env['account.move'].create.
		'''
		all_move_vals = []
		for payment in self:

			pdc_account_id = self.company_id.pdc_account_id and self.company_id.pdc_account_id.id
			if not pdc_account_id:
				raise UserError(_("Please configure pdc payment account for debtors first, from Invoicing or Accounting setting."))

			pdc_account_creditors_id = self.company_id.pdc_account_creditors_id and self.company_id.pdc_account_creditors_id.id
			if not pdc_account_creditors_id:
				raise UserError(_("Please configure pdc payment account for creditors first, from Invoicing or Accounting setting."))

			company_currency = payment.company_id.currency_id
			move_names = payment.move_name.split(payment._get_move_name_transfer_separator()) if payment.move_name else None

			# Compute amounts.
			write_off_amount = payment.payment_difference_handling == 'reconcile' and -payment.payment_difference or 0.0
			if payment.payment_type in ('outbound', 'transfer'):
				counterpart_amount = payment.amount
			else:
				counterpart_amount = -payment.amount

			# Manage currency.
			if payment.currency_id == company_currency:
				# Single-currency.
				balance = counterpart_amount
				write_off_balance = write_off_amount
				counterpart_amount = write_off_amount = 0.0
				currency_id = False
			else:
				# Multi-currencies.
				balance = payment.currency_id._convert(counterpart_amount, company_currency, payment.company_id, payment.payment_date)
				write_off_balance = payment.currency_id._convert(write_off_amount, company_currency, payment.company_id, payment.payment_date)
				currency_id = payment.currency_id.id

			# Manage custom currency on journal for liquidity line.
			if payment.journal_id.currency_id and payment.currency_id != payment.journal_id.currency_id:
				# Custom currency on journal.
				if payment.journal_id.currency_id == company_currency:
					# Single-currency
					liquidity_line_currency_id = False
				else:
					liquidity_line_currency_id = payment.journal_id.currency_id.id
				liquidity_amount = company_currency._convert(
					balance, payment.journal_id.currency_id, payment.company_id, payment.payment_date)
			else:
				# Use the payment currency.
				liquidity_line_currency_id = currency_id
				liquidity_amount = counterpart_amount

			# Compute 'name' to be used in receivable/payable line.
			rec_pay_line_name = ''
			if payment.payment_type == 'transfer':
				rec_pay_line_name = payment.name
			else:
				if payment.partner_type == 'customer':
					if payment.payment_type == 'inbound':
						rec_pay_line_name += _("Customer Payment")
					elif payment.payment_type == 'outbound':
						rec_pay_line_name += _("Customer Credit Note")
				elif payment.partner_type == 'supplier':
					if payment.payment_type == 'inbound':
						rec_pay_line_name += _("Vendor Credit Note")
					elif payment.payment_type == 'outbound':
						rec_pay_line_name += _("Vendor Payment")
				if payment.invoice_ids:
					rec_pay_line_name += ': %s' % ', '.join(payment.invoice_ids.mapped('name'))


			liquidity_line_account = payment.payment_type in ('outbound','transfer') and payment.journal_id.company_id.account_journal_payment_debit_account_id.id or payment.journal_id.company_id.account_journal_payment_credit_account_id.id
			if payment.payment_type == 'outbound':
				liquidity_line_account = pdc_account_creditors_id
			else:
				liquidity_line_account = pdc_account_id

			# Compute 'name' to be used in liquidity line.
			liquidity_line_name = payment.name
			if payment.payment_type == 'transfer':
				liquidity_line_name = _('Transfer to %s') % payment.destination_journal_id.name
			elif payment.payment_type == 'outbound':
				pdc_pay_name = str(self.env['account.account'].browse(pdc_account_creditors_id).name)+" : "+str(self.name)
				liquidity_line_name = pdc_pay_name
			else:
				pdc_pay_name = str(self.env['account.account'].browse(pdc_account_id).name)+" : "+str(self.name)
				liquidity_line_name = pdc_pay_name

			# ==== 'inbound' / 'outbound' ====

			move_vals = {
				'date': payment.payment_date,
				'ref': payment.communication,
				'move_type': 'entry',
				'journal_id': payment.journal_id.id,
				'currency_id': payment.journal_id.currency_id.id or payment.company_id.currency_id.id,
				'partner_id': payment.partner_id.id,
				'line_ids': [
					# Receivable / Payable / Transfer line.
					(0, 0, {
						'name': rec_pay_line_name,
						'amount_currency': counterpart_amount + write_off_amount if currency_id else 0.0,
						'currency_id': currency_id,
						'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
						'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
						'date_maturity': payment.payment_date,
						'partner_id': payment.partner_id.commercial_partner_id.id,
						'account_id': payment.destination_account_id.id,
						'payment_pdc_id': payment.id,
					}),
					# Liquidity line.
					(0, 0, {
						'name': liquidity_line_name,
						'amount_currency': -liquidity_amount if liquidity_line_currency_id else 0.0,
						'currency_id': liquidity_line_currency_id,
						'debit': balance < 0.0 and -balance or 0.0,
						'credit': balance > 0.0 and balance or 0.0,
						'date_maturity': payment.payment_date,
						'partner_id': payment.partner_id.commercial_partner_id.id,
						'account_id': liquidity_line_account,
						'payment_pdc_id': payment.id,
					}),
				],
			}
			if write_off_balance:
				# Write-off line.
				move_vals['line_ids'].append((0, 0, {
					'name': payment.writeoff_label,
					'amount_currency': -write_off_amount,
					'currency_id': currency_id,
					'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
					'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
					'date_maturity': payment.payment_date,
					'partner_id': payment.partner_id.commercial_partner_id.id,
					'account_id': payment.writeoff_account_id.id,
					'payment_pdc_id': payment.id,
				}))

			if move_names:
				move_vals['name'] = move_names[0]

			all_move_vals.append(move_vals)

			# ==== 'transfer' ====
			if payment.payment_type == 'transfer':
				journal = payment.destination_journal_id

				# Manage custom currency on journal for liquidity line.
				if journal.currency_id and payment.currency_id != journal.currency_id:
					# Custom currency on journal.
					liquidity_line_currency_id = journal.currency_id.id
					transfer_amount = company_currency._convert(balance, journal.currency_id, payment.company_id, payment.payment_date)
				else:
					# Use the payment currency.
					liquidity_line_currency_id = currency_id
					transfer_amount = counterpart_amount

				transfer_move_vals = {
					'date': payment.payment_date,
					'ref': payment.communication,
					'move_type': 'entry',
					'partner_id': payment.partner_id.id,
					'journal_id': payment.destination_journal_id.id,
					'line_ids': [
						# Transfer debit line.
						(0, 0, {
							'name': payment.name,
							'amount_currency': -counterpart_amount if currency_id else 0.0,
							'currency_id': currency_id,
							'debit': balance < 0.0 and -balance or 0.0,
							'credit': balance > 0.0 and balance or 0.0,
							'date_maturity': payment.payment_date,
							'partner_id': payment.partner_id.commercial_partner_id.id,
							'account_id': payment.company_id.transfer_account_id.id,
							'payment_pdc_id': payment.id,
						}),
						# Liquidity credit line.
						(0, 0, {
							'name': _('Transfer from %s') % payment.journal_id.name,
							'amount_currency': transfer_amount if liquidity_line_currency_id else 0.0,
							'currency_id': liquidity_line_currency_id,
							'debit': balance > 0.0 and balance or 0.0,
							'credit': balance < 0.0 and -balance or 0.0,
							'date_maturity': payment.payment_date,
							'partner_id': payment.partner_id.commercial_partner_id.id,
							'account_id': payment.destination_journal_id.payment_credit_account_id.id,
							'payment_pdc_id': payment.id,
						}),
					],
				}

				if move_names and len(move_names) == 2:
					transfer_move_vals['name'] = move_names[1]

				all_move_vals.append(transfer_move_vals)
		return all_move_vals


	def validate_pdc_payment(self):
		""" Posts a payment used to pay an invoice. This function only posts the
		payment by default but can be overridden to apply specific post or pre-processing.
		It is called by the "validate" button of the popup window
		triggered on invoice form by the "Register Payment" button.
		"""
		
		if any(len(record.invoice_ids) != 1 for record in self):
			# For multiple invoices, there is account.register.payments wizard
			raise UserError(_("This method should only be called to process a single invoice's payment."))

		return self.post()


	def post(self):
		""" Create the journal items for the payment and update the payment's state to 'posted'.
			A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
			and another in the destination reconcilable account (see _compute_destination_account_id).
			If invoice_ids is not empty, there will be one reconcilable move line per invoice to reconcile with.
			If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
		"""
		AccountMove = self.env['account.move'].with_context(default_type='entry')
		for rec in self:

			if rec.state != 'draft':
				raise UserError(_("Only a draft payment can be posted."))

			if any(inv.state != 'posted' for inv in rec.invoice_ids):
				raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

			pdc_account_id = self.company_id.pdc_account_id and self.company_id.pdc_account_id.id
			if not pdc_account_id:
				raise UserError(_("Please configure pdc payment account for debtors first, from Invoicing or Accounting setting."))

			pdc_account_creditors_id = self.company_id.pdc_account_creditors_id and self.company_id.pdc_account_creditors_id.id
			if not pdc_account_creditors_id:
				raise UserError(_("Please configure pdc payment account for creditors first, from Invoicing or Accounting setting."))

			# keep the name in case of a payment reset to draft
			if not rec.name:
				# Use the right sequence to set the name
				if rec.payment_type == 'transfer':
					sequence_code = 'account.payment.transfer'
				else:
					if rec.partner_type == 'customer':
						if rec.payment_type == 'inbound':
							sequence_code = 'account.payment.customer.invoice'
						if rec.payment_type == 'outbound':
							sequence_code = 'account.payment.customer.refund'
					if rec.partner_type == 'supplier':
						if rec.payment_type == 'inbound':
							sequence_code = 'account.payment.supplier.refund'
						if rec.payment_type == 'outbound':
							sequence_code = 'account.payment.supplier.invoice'
				rec.name = self.env['ir.sequence'].next_by_code(sequence_code, sequence_date=rec.payment_date)
				if not rec.name and rec.payment_type != 'transfer':
					raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))


			moves = AccountMove.create(rec._prepare_payment_moves())
			moves.action_post()

			# Update the state / move before performing any reconciliation.
			move_name = self._get_move_name_transfer_separator().join(moves.mapped('name'))
			rec.write({'state': 'posted', 'move_name': move_name})
			# if rec.payment_type in ('inbound', 'outbound'):
			if rec.payment_type == 'outbound':
				rec.write({
					'state': 'collect_cash',
					'account_move_id':moves.id,
					'pdc_account_creditors_id': pdc_account_creditors_id,
					'communication':rec.communication,
					'pdc_account_creditors_id': pdc_account_creditors_id,
					'move_name': move_name})
				
				if rec.invoice_ids:
					(moves[0] + rec.invoice_ids).line_ids \
						.filtered(lambda line: not line.reconciled and line.account_id == rec.destination_account_id)\
						.reconcile()
			elif rec.payment_type == 'transfer':
				# ==== 'transfer' ====
				moves.mapped('line_ids')\
					.filtered(lambda line: line.account_id == rec.company_id.transfer_account_id)\
					.reconcile()

			else:
				# ==== 'inbound' ====
				rec.write({
					'state': 'collect_cash',
					'account_move_id':moves.id,
					'communication':rec.communication,
					'pdc_account_id':pdc_account_id,
					'move_name': move_name
				})
				if rec.invoice_ids:
					(moves[0] + rec.invoice_ids).line_ids \
						.filtered(lambda line: not line.reconciled and line.account_id == rec.destination_account_id)\
						.reconcile()

		return True


	def button_journal_items(self):
		return {
			'name': _('Journal Items'),
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'account.move.line',
			'view_id': False,
			'type': 'ir.actions.act_window',
			'domain': ['|','|',('move_id.ref', '=', self.communication),
							('move_id.name', '=', self.communication),
						('payment_pdc_id', 'in', self.ids)],
			'context': {
				'journal_id': self.journal_id.id,
			}
		}

	def button_journal_entries(self):
		return {
			'name': _('Journal Entries'),
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'account.move',
			'view_id': False,
			'type': 'ir.actions.act_window',
			'domain': ['|',('name', '=', self.communication), ('ref', '=', self.communication)],
			'context': {
				'journal_id': self.journal_id.id,
			}
		}

	def cash_deposit_button(self):
		for record in self:
			line_ids = []
			journal = record.journal_id

			move_dict = {
				'date': fields.Date.today(),
				'ref': self.communication or '',
				'company_id': self.company_id.id,
				'journal_id': journal.id,
			}
			amount = record.amount
			if record.payment_type == 'outbound':
				debit_account_id = record.pdc_account_creditors_id.id
				credit_account_id = record.destination_account_id.id
			else:
				debit_account_id =  record.destination_account_id.id
				credit_account_id = record.pdc_account_id.id

			move_line_name = _("PDC Payment")
			if record.invoice_ids:
				move_line_name += ': '
				for inv in record.invoice_ids:
					# if inv.move_id:
					if inv.state == 'posted':
						move_line_name += inv.name + ', '
				move_line_name = move_line_name[:len(move_line_name)-2]

			if debit_account_id:
				debit_line = (0, 0, {
					'partner_id': record.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
					'move_id': record.account_move_id,
					'debit': amount > 0.0 and amount or 0.0,
					'credit': amount < 0.0 and -amount or 0.0,
					'payment_pdc_id': self.id,
					'journal_id': record.journal_id.id,
					'account_id': debit_account_id,
					'date': record.payment_date,
					'name': move_line_name
				})
				line_ids.append(debit_line)

			if credit_account_id:
				credit_line = (0, 0, {
					'partner_id': record.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
					'move_id': record.account_move_id,
					'debit': amount < 0.0 and -amount or 0.0,
					'credit': amount > 0.0 and amount or 0.0,
					'payment_pdc_id': self.id,
					'journal_id': record.journal_id.id,
					'account_id': credit_account_id,
					'date': record.payment_date,
					'name': move_line_name
				})
				line_ids.append(credit_line)
			move_dict['line_ids'] = line_ids
			move = self.env['account.move'].create(move_dict)
			move.action_post()
			return record.write({'state': 'deposited'})


	def cash_bounced_button(self):
		for record in self:
			line_ids = []
			journal = record.journal_id

			move_dict = {
				'date': fields.Date.today(),
				'ref': self.communication or '',
				'company_id': self.company_id.id,
				'journal_id': journal.id,
			}
			amount = record.amount
			if record.payment_type == 'outbound':
				debit_account_id = record.destination_account_id.id
				credit_account_id = record.pdc_account_creditors_id.id
			else:
				debit_account_id = record.pdc_account_id.id
				credit_account_id = record.destination_account_id.id

			if record.is_internal_transfer:
				move_line_name = record.name
			else:
				move_line_name = _("PDC Payment")
				if record.invoice_ids:
					move_line_name += ': '
					for inv in record.invoice_ids:
						# if inv.move_id:
						if inv.state == 'posted':
							move_line_name += inv.name + ', '
					move_line_name = move_line_name[:len(move_line_name)-2]

			if debit_account_id:
				debit_line = (0, 0, {
					'partner_id': record.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
					'move_id': record.account_move_id,
					'debit': amount > 0.0 and amount or 0.0,
					'credit': amount < 0.0 and -amount or 0.0,
					'payment_pdc_id': self.id,
					'journal_id': record.journal_id.id,
					'account_id': debit_account_id,
					'date': record.payment_date,
					'name': move_line_name
				})
				line_ids.append(debit_line)

			if credit_account_id:
				credit_line = (0, 0, {
					'partner_id': record.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
					'move_id': record.account_move_id,
					'debit': amount < 0.0 and -amount or 0.0,
					'credit': amount > 0.0 and amount or 0.0,
					'payment_pdc_id': self.id,
					'journal_id': record.journal_id.id,
					'account_id': credit_account_id,
					'date': record.payment_date,
					'name': move_line_name
				})
				line_ids.append(credit_line)
			move_dict['line_ids'] = line_ids
			move = self.env['account.move'].create(move_dict)
			move.action_post()
			return record.write({'state': 'bounced'})
	

	# collect cash done then generate journal entries
	# _create_payment_entry
	def cash_pdc_done_button(self):
		''' Helper used to dispatch the journal items between:
		- The lines using the temporary liquidity account.
		- The lines using the counterpart account.
		- The lines being the write-off lines.
		:return: (liquidity_lines, counterpart_lines, writeoff_lines)
		'''
		for record in self:

			pdc_account_id = self.company_id.pdc_account_id and self.company_id.pdc_account_id.id
			if not pdc_account_id:
				raise UserError(_("Please configure pdc payment account for debtors first, from Invoicing or Accounting setting."))

			pdc_account_creditors_id = self.company_id.pdc_account_creditors_id and self.company_id.pdc_account_creditors_id.id
			if not pdc_account_creditors_id:
				raise UserError(_("Please configure pdc payment account for creditors first, from Invoicing or Accounting setting."))

			line_ids = []
			journal = record.journal_id

			move_dict = {
				'date': fields.Date.today(),
				'ref': self.communication or '',
				'company_id': self.company_id.id,
				'journal_id': journal.id,
			}
			amount = record.amount
			if record.payment_type == 'outbound':
				debit_account_id = record.destination_account_id.id
				credit_account_id = record.pdc_account_creditors_id.id
			else:
				debit_account_id = record.pdc_account_id.id
				credit_account_id = record.destination_account_id.id

			if record.is_internal_transfer:
				move_line_name = record.name
			else:
				move_line_name = _("PDC Payment")
				if record.invoice_ids:
					move_line_name += ': '
					for inv in record.invoice_ids:
						# if inv.move_id:
						if inv.state == 'posted':
							move_line_name += inv.name + ', '
					move_line_name = move_line_name[:len(move_line_name)-2]

			if debit_account_id:
				debit_line = (0, 0, {
					'partner_id': record.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
					'move_id': record.account_move_id,
					'debit': amount > 0.0 and amount or 0.0,
					'credit': amount < 0.0 and -amount or 0.0,
					'payment_pdc_id': self.id,
					'journal_id': record.journal_id.id,
					'account_id': debit_account_id,
					'date': record.payment_date,
					'name': move_line_name
				})
				line_ids.append(debit_line)

			if credit_account_id:
				credit_line = (0, 0, {
					'partner_id': record.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
					'move_id': record.account_move_id,
					'debit': amount < 0.0 and -amount or 0.0,
					'credit': amount > 0.0 and amount or 0.0,
					'payment_pdc_id': self.id,
					'journal_id': record.journal_id.id,
					'account_id': credit_account_id,
					'date': record.payment_date,
					'name': move_line_name
				})
				line_ids.append(credit_line)
			move_dict['line_ids'] = line_ids
			move = self.env['account.move'].create(move_dict)
			move.action_post()
			return record.write({'state': 'posted'})


	def cash_returned_button(self):
		for rec in self:
			return rec.write({'state': 'returned'})


	def action_invoice_cancel(self):
		for rec in self:
			for move in rec.move_line_ids.mapped('move_id'):
				if rec.invoice_ids:
					move.line_ids.remove_move_reconcile()
				if move.state != 'draft':
					move.button_cancel()
				move.unlink()
			rec.write({
				'state': 'cancelled',
				'move_name': '',
			})

	def action_set_to_pdc_post(self):
		for rec in self:
			rec.account_move_id.button_cancel()
			rec.account_move_id.unlink()
			rec.write({
				'state': 'posted',
			})


	def pdc_due_date_remainder(self):
		today_date = datetime.today().date()
		company_id = self.company_id
		first = company_id.notify_opt_first
		second = company_id.notify_opt_second
		thired = company_id.notify_opt_thired
		vendor_notify_check = company_id.vendor_notify_check
		customer_notify_check = company_id.customer_notify_check
		user_notify_check = company_id.user_notify_check
		user_ids = company_id.user_ids
		partner_ids = company_id.partner_ids
		ven_partner_ids = company_id.ven_partner_ids
		pdc_due_date_records = self.env['pdc.account.payment'].sudo().search([('due_date','>=',today_date)])
		template_id = self.env.ref('post_dated_cheque_mgt_app.pdc_due_date_template')
		auther = self.env.user
		for record in pdc_due_date_records:
			first_option = record.due_date - relativedelta(days=int(first))
			second_option = record.due_date - relativedelta(days= int(second))
			thired_option = record.due_date - relativedelta(days=int(thired))
			if first_option == today_date:
				if user_notify_check:
					for user in user_ids:
						values = template_id.sudo().generate_email(record.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
						values['email_to'] = user.partner_id.email or ''
						mail_mail_obj = self.env['mail.mail']
						msg_id = mail_mail_obj.sudo().create(values)
						if msg_id:
							msg_id.sudo().send()
				if customer_notify_check:
					for partner in partner_ids:
						values = template_id.sudo().generate_email(record.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
						values['email_to'] = partner.email or ''
						mail_mail_obj = self.env['mail.mail']
						msg_id = mail_mail_obj.sudo().create(values)
						if msg_id:
							msg_id.sudo().send()
				if vendor_notify_check:
					for partner in ven_partner_ids:
						values = template_id.sudo().generate_email(record.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
						values['email_to'] = partner.email or ''
						mail_mail_obj = self.env['mail.mail']
						msg_id = mail_mail_obj.sudo().create(values)
						if msg_id:
							msg_id.sudo().send()
			if second_option ==  today_date:
				if user_notify_check:
					for user in user_ids:
						values = template_id.sudo().generate_email(record.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
						values['email_to'] = user.partner_id.email or ''
						mail_mail_obj = self.env['mail.mail']
						msg_id = mail_mail_obj.sudo().create(values)
						if msg_id:
							msg_id.sudo().send()
				if customer_notify_check:
					for partner in partner_ids:
						values = template_id.sudo().generate_email(record.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
						values['email_to'] = partner.email or ''
						mail_mail_obj = self.env['mail.mail']
						msg_id = mail_mail_obj.sudo().create(values)
						if msg_id:
							msg_id.sudo().send()
				if vendor_notify_check:
					for partner in ven_partner_ids:
						values = template_id.sudo().generate_email(record.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
						values['email_to'] = partner.email or ''
						mail_mail_obj = self.env['mail.mail']
						msg_id = mail_mail_obj.sudo().create(values)
						if msg_id:
							msg_id.sudo().send()
			if thired_option ==  today_date:
				if user_notify_check:
					for user in user_ids:
						values = template_id.sudo().generate_email(record.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
						values['email_to'] = user.partner_id.email or ''
						mail_mail_obj = self.env['mail.mail']
						msg_id = mail_mail_obj.sudo().create(values)
						if msg_id:
							msg_id.sudo().send()
				if customer_notify_check:
					for partner in partner_ids:
						values = template_id.sudo().generate_email(record.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
						values['email_to'] = partner.email or ''
						mail_mail_obj = self.env['mail.mail']
						msg_id = mail_mail_obj.sudo().create(values)
						if msg_id:
							msg_id.sudo().send()
				if vendor_notify_check:
					for partner in ven_partner_ids:
						values = template_id.sudo().generate_email(record.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
						values['email_to'] = partner.email or ''
						mail_mail_obj = self.env['mail.mail']
						msg_id = mail_mail_obj.sudo().create(values)
						if msg_id:
							msg_id.sudo().send()
		return True
