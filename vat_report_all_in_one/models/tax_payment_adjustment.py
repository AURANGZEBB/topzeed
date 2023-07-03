from odoo import models, fields, api


class TaxPaymentAdjustment(models.TransientModel):
    _name = 'tax.payment.adjustment.wizard'

    @api.onchange('vat_type')
    def _get_journal_domain(self):
        if self.vat_type in ('payment', 'refund'):
            journal_ids = self.env['account.journal'].search([('type', 'in', ('bank', 'cash'))]).ids
        elif self.vat_type == 'adjustment':
            journal_ids = self.env['account.journal'].search([]).ids
        else:
            journal_ids = []
        return {'domain': {'journal_id': [('id', 'in', journal_ids)]}}

    name = fields.Char('Reason')
    amount = fields.Monetary('Amount')
    vat_type = fields.Selection([('payment', 'Payment'), ('refund', 'Refund'), ('adjustment', 'Manaul Adjustment')], string='Type', defaul='payment')
    debit_account_id = fields.Many2one('account.account', string='Debit Account')
    credit_account_id = fields.Many2one('account.account', string='Credit Account')
    journal_id = fields.Many2one('account.journal', string='Journal')
    date = fields.Date('Date')
    adjustment_type = fields.Selection([('debit', 'Applied on debit journal item'), ('credit', 'Applied on credit journal item')], string="Adjustment Type")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id.id)

    def create_move(self):
        move_line_vals = []

        if self.vat_type == 'adjustment':
            is_debit = self.adjustment_type == 'debit'
        else:
            is_debit = self.vat_type == 'payment'

        # Vals for the amls corresponding to the ajustment tag
        if self.vat_type == 'adjustment':
            move_line_vals.append((0, 0, {
                'name': self.name,
                'debit': is_debit and abs(self.amount) or 0,
                'credit': not is_debit and abs(self.amount) or 0,
                'account_id': is_debit and self.debit_account_id.id or self.credit_account_id.id,
                'vat_payment_adj_type': self.vat_type
            }))
            move_line_vals.append((0, 0, {
                'name': self.name,
                'debit': not is_debit and abs(self.amount) or 0,
                'credit': is_debit and abs(self.amount) or 0,
                'account_id': is_debit and self.credit_account_id.id or self.debit_account_id.id,
                'vat_payment_adj_type': self.vat_type
            }))
        else:
            move_line_vals.append((0, 0, {
                'name': self.name,
                'debit': is_debit and abs(self.amount) or 0,
                'credit': not is_debit and abs(self.amount) or 0,
                'account_id': not is_debit and self.debit_account_id.id or self.credit_account_id.id,
                'vat_payment_adj_type': self.vat_type
            }))
            move_line_vals.append((0, 0, {
                'name': self.name,
                'debit': not is_debit and abs(self.amount) or 0,
                'credit': is_debit and abs(self.amount) or 0,
                'account_id': self.journal_id.default_account_id.id,
                'vat_payment_adj_type': self.vat_type
            }))

        # Create the move
        vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'state': 'draft',
            'line_ids': move_line_vals,
        }
        move = self.env['account.move'].create(vals)
        move.post()

        # Return an action opening the created move
        action = self.env.ref(self.env.context.get('action', 'account.action_move_line_form'))
        result = action.read()[0]
        result['views'] = [(False, 'form')]
        result['res_id'] = move.id
        return result
