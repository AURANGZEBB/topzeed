from odoo import fields,models,api,_



class AccountPayment(models.Model):
    _inherit = 'account.payment'


    sale_id = fields.Many2one('sale.order',string='Sale Order',copy=False)



class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_count = fields.Integer('Payment Count',compute='_compute_payment_count',copy=False)
    payment_ids = fields.One2many('account.payment','sale_id',string='Payments',copy=False)


    @api.depends('state','payment_ids.state')
    def _compute_payment_count(self):
        for sale in self:
            qty = 0
            for payment in self.payment_ids:
                qty += 1
            sale.payment_count = qty


    def action_view_payment_ids(self):
        # self.ensure_one()
        view_form_id = self.env.ref('account.view_account_payment_form').id
        view_tree_id = self.env.ref('account.view_account_payment_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.payment_ids.ids)],
            'view_mode': 'tree,form',
            'name': _('Payments'),
            'res_model': 'account.payment',
        }
        if len(self.payment_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.payment_ids.id})
        else:
            action['views'] = [(view_tree_id, 'tree'), (view_form_id, 'form')]
        return action

    def open_tamm_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www1.tamm.net.sa/CarPortalWeb/index.jsp',
            'target': '_blank',
        }