# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import odoo.addons.decimal_precision as dp
from odoo import api, fields, models, _


class sale_order(models.Model):
	_inherit = 'sale.order'

	@api.depends('discount_amount','discount_method')
	def _calculate_discount(self):
		res=0.0
		discount = 0.0
		for self_obj in self:
			if self_obj.discount_method == 'fix':
				discount = self_obj.discount_amount
				res = discount
			elif self_obj.discount_method == 'per':
				discount = self_obj.amount_untaxed * (self_obj.discount_amount/ 100)
				res = discount
			else:
				res = discount
		return res


	@api.depends('order_line','order_line.price_total','order_line.price_subtotal',\
        'order_line.product_uom_qty','discount_amount',\
        'discount_method')
	def _amount_all(self):
		"""
		Compute the total amounts of the SO.
		"""
		cur_obj = self.env['res.currency']
		for order in self:
			amount_untaxed = amount_tax = 0.0
			for line in order.order_line:
				amount_untaxed += line.price_subtotal
				amount_tax += line.price_tax

			order.update({
						  'amount_untaxed': amount_untaxed,
						  'amount_tax': amount_tax,
						  'amount_total': amount_untaxed + amount_tax,
						  })
			res = self._calculate_discount()
			order.update({'discount_amt' : res,
						  'amount_total': amount_untaxed + amount_tax-res
						  })


	discount_method = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')], 'Discount Method')
	discount_amount = fields.Float('Discount Amount')
	discount_amt = fields.Monetary(compute='_amount_all', string='- Discount', store=True, readonly=True)

	def _prepare_invoice(self):
		"""
		Prepare the dict of values to create the new invoice for a sales order. This method may be
		overridden to implement custom invoice generation (making sure to call super() to establish
		a clean extension chain).
		"""
		self.ensure_one()
		# ensure a correct context for the _get_default_journal method and company-dependent fields
		self = self.with_context(default_company_id=self.company_id.id, force_company=self.company_id.id)
		journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
		if not journal:
			raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (self.company_id.name, self.company_id.id))

		invoice_vals = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.pricelist_id.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'invoice_user_id': self.user_id and self.user_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(self.partner_invoice_id.id)).id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
			'discount_method': self.discount_method,
			'discount_amount': self.discount_amount,
			'discount_amt': self.discount_amt,
		}
		return invoice_vals        




class sale_order_line(models.Model):
	_inherit = 'sale.order.line'

	is_apply_on_discount_amount =  fields.Boolean("Tax Apply After Discount")
	discount_method = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')], 'Discount Method')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:s
