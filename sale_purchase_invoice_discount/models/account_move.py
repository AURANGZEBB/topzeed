# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.tools import float_is_zero
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re

class account_move(models.Model):
    _inherit = 'account.move'

    discount_method = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')],'Discount Method')
    discount_amount = fields.Float('Discount Amount')
    discount_amt = fields.Float(string='- Discount', readonly=True, compute='_compute_amount')
    amount_untaxed = fields.Float(string='Subtotal', digits="Account",store=True, readonly=True, compute='_compute_amount',tracking=True)
    amount_tax = fields.Float(string='Tax', digits="Account",store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Float(string='Total', digits="Account",store=True, readonly=True, compute='_compute_amount')


    def calc_discount(self):
        for calc in self:
            calc._calculate_discount()


    @api.depends('discount_amount','discount_method')
    def _calculate_discount(self):
        res = discount = 0.0
        for self_obj in self:
            if self_obj.discount_method == 'fix':
                res = self_obj.discount_amount
            elif self_obj.discount_method == 'per':
                res = self_obj.amount_untaxed * (self_obj.discount_amount/ 100)
            else:
                res = discount
        return res


    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id','discount_method','discount_amount')
    def _compute_amount(self):
        for move in self:

            if move.payment_state == 'invoicing_legacy':
                # invoicing_legacy state is set via SQL when setting setting field
                # invoicing_switch_threshold (defined in account_accountant).
                # The only way of going out of this state is through this setting,
                # so we don't recompute it here.
                move.payment_state = move.payment_state
                continue

            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_to_pay = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            total = 0.0
            total_currency = 0.0
            currencies = move._get_lines_onchange_currency().currency_id
            move.discount_amt = 0.0

            for line in move.line_ids:
                if move._payment_state_matters():
                    # === Invoices ===

                    if not line.exclude_from_invoice_tab:
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.tax_line_id:
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.account_id.user_type_id.type in ('receivable', 'payable'):
                        # Residual amount.
                        total_to_pay += line.balance
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            if move.move_type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1
            move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
            move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
            move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual

            currency = currencies if len(currencies) == 1 else move.company_id.currency_id

            # Compute 'payment_state'.
            new_pmt_state = 'not_paid' if move.move_type != 'entry' else False

            if move._payment_state_matters() and move.state == 'posted':

                if currency.is_zero(move.amount_residual):
                    reconciled_payments = move._get_reconciled_payments()
                    if not reconciled_payments or all(payment.is_matched for payment in reconciled_payments):
                        new_pmt_state = 'paid'
                    else:
                        new_pmt_state = move._get_invoice_in_payment_state()
                elif currency.compare_amounts(total_to_pay, total_residual) != 0:
                    new_pmt_state = 'partial'

            if new_pmt_state == 'paid' and move.move_type in ('in_invoice', 'out_invoice', 'entry'):
                reverse_type = move.move_type == 'in_invoice' and 'in_refund' or move.move_type == 'out_invoice' and 'out_refund' or 'entry'
                reverse_moves = self.env['account.move'].search([('reversed_entry_id', '=', move.id), ('state', '=', 'posted'), ('move_type', '=', reverse_type)])

                # We only set 'reversed' state in cas of 1 to 1 full reconciliation with a reverse entry; otherwise, we use the regular 'paid' state
                reverse_moves_full_recs = reverse_moves.mapped('line_ids.full_reconcile_id')
                if reverse_moves_full_recs.mapped('reconciled_line_ids.move_id').filtered(lambda x: x not in (reverse_moves + reverse_moves_full_recs.mapped('exchange_move_id'))) == move:
                    new_pmt_state = 'reversed'

            move.payment_state = new_pmt_state
            #Calculate Discount
            move.amount_untaxed = sum(line.price_subtotal for line in move.invoice_line_ids)
            res = move._calculate_discount()
            move.discount_amt = res
            move.amount_total = move.amount_untaxed - res + move.amount_tax
            amount_total_company_signed = move.amount_total
            amount_untaxed_signed = move.amount_untaxed
            if move.currency_id and move.currency_id != move.company_id.currency_id:
                amount_total_company_signed = move.currency_id.compute(move.amount_total, move.company_id.currency_id)
                amount_untaxed_signed = move.currency_id.compute(move.amount_untaxed, move.company_id.currency_id)
            sign = move.move_type in ['in_refund', 'out_refund'] and -1 or 1
            move.amount_total_signed = move.amount_total * sign
            move.amount_untaxed_signed = amount_untaxed_signed * sign


    @api.onchange('invoice_line_ids', 'discount_method', 'discount_amount')
    def _onchange_invoice_line_ids(self):
        current_invoice_lines = self.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)
        others_lines = self.line_ids - current_invoice_lines
        if others_lines and current_invoice_lines - self.invoice_line_ids:
            others_lines[0].recompute_tax_line = True
        if self.move_type != 'entry' and self.state in 'draft' and self.discount_method in ('fix','per') and self.discount_amount > 0:
            self._compute_amount()
            for rec in self.line_ids:
                if rec.name == "Discount":
                    rec.with_context(check_move_validity=False).write({'price_unit':-self.discount_amt})
                if self._context.get('default_move_type') == 'in_invoice':
                    if rec.name == False or rec.name == '':
                        rec.with_context(check_move_validity=False).write({'credit':self.amount_total})
                else:
                    pass
        self.line_ids = others_lines + self.invoice_line_ids
        self._onchange_recompute_dynamic_lines()


    @api.model_create_multi
    def create(self, vals_list):
        result = super(account_move,self).create(vals_list)
        for res in result:
            if res.move_type != 'entry' and res.state in 'draft' and res.discount_method in ('fix','per') and res.discount_amount > 0:
                account = False
                for line in res.invoice_line_ids:
                    if line.product_id:
                        account = line.account_id.id
                l = res.line_ids.filtered(lambda s: s.name == 'Discount')
                if len(l or []) == 0 and account:
                    discount_vals = {
                        'account_id': account, 
                        'quantity': 1,
                        'price_unit': -res.discount_amt,
                        'name': "Discount", 
                        'exclude_from_invoice_tab': True,
                    } 
                    res.with_context(check_move_validity=False).write({
                            'invoice_line_ids' : [(0,0,discount_vals)]
                        })

        return result


    def write(self,vals):
        result = super(account_move,self).write(vals)
        for res in self:
            if res.move_type != 'entry' and res.state in 'draft' and res.discount_method in ('fix','per') and res.discount_amount > 0:
                account = False
                for line in res.invoice_line_ids:
                    if line.product_id:
                        account = line.account_id.id
                l = res.line_ids.filtered(lambda s: s.name == 'Discount')
                if len(l or []) == 0 and account:
                    discount_vals = {
                        'account_id': account, 
                        'quantity': 1,
                        'price_unit': -res.discount_amt,
                        'name': "Discount", 
                        'exclude_from_invoice_tab': True,
                    } 
        
                    res.with_context(check_move_validity=False).write({
                            'invoice_line_ids' : [(0,0,discount_vals)]
                        })
        return result                           




class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def _create_tax_cash_basis_moves(self):
        ''' Create the tax cash basis journal entries.
        :return: The newly created journal entries.
        '''
        tax_cash_basis_values_per_move = self._collect_tax_cash_basis_values()

        moves_to_create = []
        to_reconcile_after = []
        for move_values in tax_cash_basis_values_per_move.values():
            move = move_values['move']
            pending_cash_basis_lines = []

            for i, partial_values in enumerate(move_values['partials']):
                partial = partial_values['partial']
                is_last_partial = i == len(move_values['partials']) - 1

                # Init the journal entry.
                move_vals = {
                    'move_type': 'entry',
                    'date': partial.max_date,
                    'ref': move.name,
                    'journal_id': partial.company_id.tax_cash_basis_journal_id.id,
                    'line_ids': [],
                    'tax_cash_basis_rec_id': partial.id,
                    'tax_cash_basis_origin_move_id': move.id,
                    'fiscal_position_id': move.fiscal_position_id.id,
                }

                # Tracking of lines grouped all together.
                # Used to reduce the number of generated lines and to avoid rounding issues.
                partial_lines_to_create = {}

                for caba_treatment, line in move_values['to_process_lines']:

                    # ==========================================================================
                    # Compute the balance of the current line on the cash basis entry.
                    # This balance is a percentage representing the part of the journal entry
                    # that is actually paid by the current partial.
                    # ==========================================================================

                    # Percentage expressed in the foreign currency.
                    amount_currency = line.currency_id.round(line.amount_currency * partial_values['percentage'])
                    balance = partial_values['payment_rate'] and amount_currency / partial_values['payment_rate'] or 0.0

                    # ==========================================================================
                    # Prepare the mirror cash basis journal item of the current line.
                    # Group them all together as much as possible to reduce the number of
                    # generated journal items.
                    # Also track the computed balance in order to avoid rounding issues when
                    # the journal entry will be fully paid. At that case, we expect the exact
                    # amount of each line has been covered by the cash basis journal entries
                    # and well reported in the Tax Report.
                    # ==========================================================================

                    if caba_treatment == 'tax':
                        # Tax line.

                        cb_tax_line_vals = self._prepare_cash_basis_tax_line_vals(line, balance, amount_currency)
                        grouping_key = self._get_cash_basis_tax_line_grouping_key_from_vals(cb_tax_line_vals)
                        partial_lines_to_create[grouping_key] = {
                            'tax_line': line,
                            'vals': cb_tax_line_vals,
                        }

                    elif caba_treatment == 'base':
                        # Base line.

                        cb_base_line_vals = self._prepare_cash_basis_base_line_vals(line, balance, amount_currency)
                        grouping_key = self._get_cash_basis_base_line_grouping_key_from_vals(cb_base_line_vals)

                        if grouping_key in partial_lines_to_create:
                            aggregated_vals = partial_lines_to_create[grouping_key]['vals']
                            balance = aggregated_vals['debit'] - aggregated_vals['credit']
                            balance += cb_base_line_vals['debit'] - cb_base_line_vals['credit']

                            aggregated_vals.update({
                                'debit': balance if balance > 0.0 else 0.0,
                                'credit': -balance if balance < 0.0 else 0.0,
                            })
                            aggregated_vals['amount_currency'] += cb_base_line_vals['amount_currency']
                        else:
                            partial_lines_to_create[grouping_key] = {
                                'vals': cb_base_line_vals,
                            }

                # ==========================================================================
                # Ensure the full coverage by replacing the balance of the journal items
                # created by the last partial.
                # ==========================================================================

                if move_values['is_fully_paid'] and is_last_partial:
                    self._fix_cash_basis_full_balance_coverage(
                        move_values,
                        partial_values,
                        pending_cash_basis_lines,
                        partial_lines_to_create,
                    )

                # ==========================================================================
                # Create the counterpart journal items.
                # ==========================================================================

                # To be able to retrieve the correct matching between the tax lines to reconcile
                # later, the lines will be created using a specific sequence.
                sequence = 0

                for grouping_key, aggregated_vals in partial_lines_to_create.items():
                    line_vals = aggregated_vals['vals']
                    line_vals['sequence'] = sequence

                    pending_cash_basis_lines.append((grouping_key, line_vals['amount_currency']))

                    if 'tax_repartition_line_id' in line_vals:
                        # Tax line.

                        tax_line = aggregated_vals['tax_line']
                        counterpart_line_vals = self._prepare_cash_basis_counterpart_tax_line_vals(tax_line, line_vals)
                        counterpart_line_vals['sequence'] = sequence + 1

                        if tax_line.account_id.reconcile:
                            move_index = len(moves_to_create)
                            to_reconcile_after.append((tax_line, move_index, counterpart_line_vals['sequence']))

                    else:
                        # Base line.

                        counterpart_line_vals = self._prepare_cash_basis_counterpart_base_line_vals(line_vals)
                        counterpart_line_vals['sequence'] = sequence + 1

                    sequence += 2

                    move_vals['line_ids'] += [(0, 0, counterpart_line_vals), (0, 0, line_vals)]

                moves_to_create.append(move_vals)

        moves = self.env['account.move'].create(moves_to_create)
        if moves:
            moves._post(soft=False)

        # Reconcile the tax lines being on a reconcile tax basis transfer account.
        for line, move_index, sequence in to_reconcile_after:
            counterpart_line = moves[move_index].line_ids.filtered(lambda line: line.sequence == sequence)

            # When dealing with tiny amounts, the line could have a zero amount and then, be already reconciled.
            if counterpart_line.reconciled:
                continue

            (line + counterpart_line).reconcile()

        return moves