# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp

class purchase_order(models.Model):
    _inherit = 'purchase.order'

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
      


    def action_view_invoice(self, invoices=False):
        """This function returns an action that display existing vendor bills of
        given purchase order ids. When only one found, show the vendor bill
        immediately.
        """
        if not invoices:
            # Invoice_ids may be filtered depending on the user. To ensure we get all
            # invoices related to the purchase order, we read them in sudo to fill the
            # cache.
            self.sudo()._read(['invoice_ids'])
            invoices = self.invoice_ids

        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        invoices.write({
            'discount_amt' : self.discount_amt, 
            'discount_method' : self.discount_method, 
            'discount_amount' : self.discount_amount, 
            'amount_untaxed' : self.amount_untaxed,
            'amount_total':self.amount_total

        })

        # choose the view_mode accordingly
        if len(invoices) > 1:
            result['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = invoices.id
        else:
            result = {'type': 'ir.actions.act_window_close'}

        return result


    discount_method = fields.Selection(
            [('fix', 'Fixed'), ('per', 'Percentage')], 'Discount Method')
    discount_amount = fields.Float('Discount Amount')
    discount_amt = fields.Monetary(compute='_calculate_discount',store=True,string='- Discount',readonly=True)
        
    amount_untaxed = fields.Monetary(string='Untaxed Amount',store=True ,readonly=True,compute='_amount_all',tracking=True)
    amount_tax = fields.Monetary(string='Taxes', readonly=True, store=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total',readonly=True,store=True,compute='_amount_all',tracking=True)
    
    
class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'

    discount_method = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')], 'Discount Method')


    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(**line._prepare_compute_all_values())
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:s
