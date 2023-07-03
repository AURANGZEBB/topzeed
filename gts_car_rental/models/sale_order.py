# -*- coding: utf-8 -*-

from odoo import models, api, fields,_
from odoo.exceptions import UserError, ValidationError, AccessError, MissingError, AccessDenied
from odoo.tools import float_is_zero,float_compare
import datetime
# from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends('order_line.state', 'order_line.product_uom_qty', 'order_line.qty_delivered', 'order_line.qty_to_invoice', 'order_line.qty_invoiced')
    def _compute_invoiced_quantity(self):
        for sale in self:
            qty = 0.0
            for line in sale.order_line:
                qty = line.qty_invoiced
            sale.qty_invoiced = qty


    car_rental_flag = fields.Boolean('Car Rental Flag', default=False)
    amount_total = fields.Float(string='Total', store=True, readonly=True, compute='_amount_all', tracking=4,digits=(16,0))
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    driver_id = fields.Many2one('res.partner', string="Driver")
    date_start = fields.Datetime(string="Booking From")
    # time_start = fields.Float(string='From Time')
    date_end = fields.Datetime(string="Booking Till")
    # time_end = fields.Float(string="Till Time")
    date = fields.Date(default=fields.Date.context_today)
    unit = fields.Selection(related='vehicle_id.odometer_unit', string="Unit", readonly=True)
    value = fields.Float('Odometer Value')
    odometer_ids = fields.One2many('fleet.vehicle.odometer', 'odometer_id', 'odometer')
    iqama_id = fields.Char('IQAMA/ID No',related='partner_id.iqama_no',store=True)
    driving_number = fields.Char('Driving License No',related='partner_id.iqama_no',store=True)
    doc_attachment_id = fields.Binary('Document', attachment=True)
    check_in = fields.Boolean('Check In', default=False,copy=False)
    check_out = fields.Boolean('Check Out', default=False,copy=False)
    status = fields.Selection([
        ('checkin','Checked-In'),
        ('checkin_pending', 'Check-In Pending'),
        ('checkout_pending', 'Check-Out Pending'),
        ('checkout', 'Checked-Out')
        ], string='Car Status', index=True, tracking=2,default='checkin')
    advance_payment = fields.Float(string='Advanced Payment', tracking=True)
    security_deposit = fields.Float(string='Security Deposit',tracking=True)
    # compute = '_default_security_deposit'
    allowed_odometer = fields.Float(string='Daily Allowed KM',tracking=True, store=True,compute='_compute_allowed_distance')
    # extra_charges = fields.Float(string='Rate for extra hours',tracking=True,store=True,compute='_compute_extra_charges')
    actualy_checkin = fields.Datetime('Actual Checked-In',copy=False)
    actualy_checked = fields.Datetime('Actual Checked-Out',copy=False)
    extra_hour_charges = fields.Float(string='Ext. hour Charges', tracking=True, store=True,
                                      compute='_compute_extra_charges')
    extra_odometer_charges = fields.Float(string='Ext. Odometer Charges', tracking=True, store=True,
                                          compute='_compute_extra_charges')
    chargable_odometer_reading = fields.Float(string='Ext. Billable Odometer', tracking=True, store=True)
    chargable_extra_hours = fields.Float(string='Ext. Billable Hours', tracking=True, store=True)
    total_odometer_cost = fields.Float(string='Total Ext Odometer Price', tracking=True, store=True,copy=False)
    total_hours_cost = fields.Float(string='Total Ext. Hours Price', tracking=True, store=True,copy=False)
    expected_hours = fields.Char(string='Exptd Service Hours',store=True,compute='_compute_expected')
    expected_distance = fields.Float(string='Exptd Distance',store=True,compute='_compute_expected',digits=(4,2))
    booking_type = fields.Selection(selection=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly')
        ], string='Booking Type', required=True,
        help='Select the Booking type')
    total_extra_price = fields.Float('Total Extra Price',compute='_compute_extra_price',copy=False)
    total_extra_price_without_taxes = fields.Float('Total Extra Price (Without Taxes)')
    total_taxes = fields.Float('Total Taxes')
    total_extra_price_with_taxes = fields.Float('Total Extra Price (With Taxes)')
    total_amount_paid = fields.Float('Total Amount Paid', store=True,copy=False)
    extra_daily_charges = fields.Float(string='Extra Daily Chageres', help='Extra Chageres for the Car after Booked Duration.', store=True, compute='_compute_extra_charges')
    additional_driver_details = fields.Text(string='Additional Driver Details')
    tamm_authorization = fields.Boolean(string='Tamm Authorization')
    remaining_amount = fields.Float('Recievable Amount')
    returning_amount = fields.Float('Amount To Return')
    invoice_amount = fields.Float('Invoice Amount')
    service_day = fields.Float('Number of Days', store=True,copy=False,compute='_compute_service_day')
    actual_day = fields.Float('Actual no of Days', store=True,copy=False,compute='_compute_actual_service_day')
    extra_day = fields.Float('Day Count',store=True,copy=False)
    qty_invoiced = fields.Float('Invoiced Quantity',store = True,copy=False,compute=_compute_invoiced_quantity)


    @api.depends('date_start','date_end')
    def _compute_service_day(self):
        days = 0
        for order in self:
            if order.date_end and order.date_start:
                start = order.date_start.date()
                end = order.date_end.date()
                temp = end - start
                days = temp.days
                print('=================',days,start,end)
            order.service_day = days
        return days


    @api.depends('actualy_checkin', 'actualy_checked')
    def _compute_actual_service_day(self):
        days = 0
        for order in self:
            if order.actualy_checkin and order.actualy_checked:
                start = order.actualy_checked.date()
                end = order.actualy_checkin.date()
                temp = end - start
                days = temp.days
                print('=================', days, start, end)
            order.actual_day = days
        return days



    @api.depends('total_odometer_cost','total_hours_cost')
    def _compute_extra_price(self):
        total = 0.0
        for record in self:
            if record.total_odometer_cost:
                total += record.total_odometer_cost
            if record.total_hours_cost:
                print('ewrtgfdfg345635746543')
                total += record.total_hours_cost
            record.total_extra_price = total

        return total

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        # return self.env.company.default_amount
        for record in self:
            if record.partner_id:
                record.driver_id = record.partner_id

    @api.depends('order_line.product_id')
    def _compute_expected(self):
        for sale in self:
            if sale.date_start or sale.date_end:
                service_duration = sale.date_end - sale.date_start
                sale.expected_hours = service_duration.total_seconds() / 3600

            if sale.date_start or sale.date_end or sale.allowed_odometer:

                actual_duration = sale.date_end - sale.date_start
                print('2345434543',actual_duration)
                actual_duration_in_seconds = 0.0
                if actual_duration:
                    actual_duration_in_seconds = actual_duration.total_seconds()
                print('insencond', actual_duration_in_seconds)
                actual_duration_in_hours = actual_duration_in_seconds // 3600
                temp_actual_duration_in_mins = actual_duration_in_seconds % 3600
                print('tcyvbgfxdcghjbk', temp_actual_duration_in_mins)
                actual_duration_in_mins = 0.0
                if temp_actual_duration_in_mins > 1:
                    actual_duration_in_mins = temp_actual_duration_in_mins / 60
                # print(actual_duration_in_mins)
                actual_allowed_distance_per_hour = sale.allowed_odometer / 24
                total_distance_allowed = actual_allowed_distance_per_hour * actual_duration_in_hours + (
                            actual_allowed_distance_per_hour * (actual_duration_in_mins / 60))
                sale.expected_distance = total_distance_allowed

                self.advance_payment = self.amount_total

    def _compute_count_all(self):
        res = super(SaleOrder, self)._compute_count_all()
        Odometer = self.env['sale.order']
        for record in self:
            record.odometer_count = Odometer.search_count([('vehicle_id', '=', record.id)])

        return res

    def action_checkin(self):
        ctx = {
            'default_checkout': False,
            'default_checkin': True,
            'default_amount_paid': self.total_amount_paid,
            'default_total_bill': self.amount_total,
            'default_actual_date': fields.Datetime.now(),
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'document.attachment',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def action_checkout(self):
        if self.tamm_authorization == False:
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'tamm.authorization',
                'views': [(False, 'form')],
                'view_id': False,
                'target': 'new',
            }

        payment = self.env['account.payment'].search([('payment_type','=','inbound'),('ref','=',self.name)])
        if payment:
            total = 0.0
            for paid in payment:
                total += paid.amount
            self.total_amount_paid = total
        ctx = {
            'default_checkout': True,
            'default_checkin': False,
            'default_actual_date':self.date_start
        }
        if self.total_amount_paid > (self.security_deposit + self.advance_payment) or self.total_amount_paid == (self.security_deposit + self.advance_payment):
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'document.attachment',
                'views': [(False, 'form')],
                'view_id': False,
                'target': 'new',
                'context': ctx,
            }
        else:
            raise UserError(_('Please Take Full Security Deposit Amount'))


    def compute_paid_amount(self):
        payment = self.env['account.payment'].search([('payment_type', '=', 'inbound'), ('ref', '=', self.name),('state','=','posted')])
        total = 0.0
        if payment:
            for paid in payment:
                total += paid.amount
            self.total_amount_paid = total
        else:
            self.total_amount_paid = total





    def action_confirm(self):
        if self.car_rental_flag and not self.date_start:
            raise MissingError(_('Please Enter Start Date !!!'))
        if self.car_rental_flag and not self.date_end:
            raise MissingError(_('Please Enter End Date !!!'))
        if self.car_rental_flag and not self.vehicle_id:
            raise MissingError(_('Please Select Vehicle !!!'))
        if self.car_rental_flag and not self.driver_id:
            raise MissingError(_('Please Select Driver !!!'))
        if self.car_rental_flag and not self.date_start:
            raise MissingError(_('Please Enter Start Date'))
        if self.car_rental_flag and not self.date_start:
            raise MissingError(_('Please Enter Start Date'))
        if self.car_rental_flag and not self.iqama_id:
            raise MissingError(_('Please Enter IQAMA/ID No Document'))
        res = super(SaleOrder, self).action_confirm()
        if self.status == 'checkin':
            self.status = 'checkout_pending'
        return res

    @api.depends('order_line.product_id','order_line.product_uom_qty','order_line.price_unit')
    def _compute_allowed_distance(self):
        for sale in self:
            print('sale order')
            for order in sale.order_line:
                if order.product_id:
                    sale.allowed_odometer = order.product_id.allowed_odometer
                    #sale.extra_charges = order.product_id.extra_charges
                    # print('order.product_id.extra_charges',order.product_id.extra_charges)

    @api.depends('order_line.product_id', 'order_line.product_uom_qty', 'order_line.price_unit')
    def _compute_extra_charges(self):
        for sale in self:
            print('sale order')
            for order in sale.order_line:
                if order.product_id:
                    #sale.allowed_distance = order.product_id.allow_distance
                    sale.extra_hour_charges = order.product_id.extra_hour_charges
                    sale.extra_odometer_charges = order.product_id.extra_odometer_charges
                    sale.extra_daily_charges = order.product_id.extra_daily_charges
                    print('order.product_id.extra_charges', order.product_id.extra_hour_charges)

    # @api.depends('order_line.product_id', 'order_line.product_uom_qty', 'order_line.price_unit')
    # def _compute_daily_extra_charges(self):
    #     for sale in self:
    #         print('sale order')
    #         for order in sale.order_line:
    #             if order.product_id:
    #                 sale.extra_daily_charges = order.product_id.extra_daily_charges

    def action_register_advance_payment(self):
        return {
            'name': _('Register Payment'),
            'res_model': 'account.advance.payment',
            'view_mode': 'form',
            'context': {
                'active_model': 'sale.order',
                'active_ids': self.ids,
                'default_res_id': self.ids[0],
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_company_id': self.env.company.id,
                'default_partner_id': self.partner_id.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
    def action_register_deposit_return(self):
        return {
            'name': _('Register Payment'),
            'res_model': 'account.deposit.payment',
            'view_mode': 'form',
            'context': {
                'active_model': 'sale.order',
                'active_ids': self.ids,
                'default_res_id': self.ids[0],
                'default_payment_type': 'outbound',
                'default_partner_type': 'customer',
                'default_company_id': self.env.company.id,
                'default_partner_id': self.partner_id.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def compute_due_amount(self):
        # actual_date = datetime.datetime.now()
        # actual_duration = self.actual_date - self.date_start
        # actual_duration_in_seconds = actual_duration.total_seconds()
        # print('insencond', actual_duration_in_seconds)
        # actual_duration_in_hours = actual_duration_in_seconds // 3600
        # temp_actual_duration_in_mins = actual_duration_in_seconds % 3600
        # print('tcyvbgfxdcghjbk', temp_actual_duration_in_mins)
        # actual_duration_in_mins = 0.0
        # if temp_actual_duration_in_mins > 1:
        #     actual_duration_in_mins = temp_actual_duration_in_mins / 60
        # print(actual_duration_in_mins)
        #
        # if self.date_end < actual_date:
        #     extra_duration = actual_date - self.date_end
        #     extra_duration_in_seconds = extra_duration.total_seconds()
        #     extra_duration_in_hours = extra_duration_in_seconds // 3600
        #     self.chargable_extra_hours = extra_duration_in_hours
        #     self.total_hours_cost = extra_duration_in_hours * self.extra_hour_charges
        ctx = {
            'default_checkin': self.date_end,
            'default_checkout': self.date_start,
            'default_paid_amount': self.total_amount_paid,
            'default_total_bill': self.amount_total,
            'default_actual_date': fields.Datetime.now(),
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'due.amount',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def _get_tax(self):
        for order in self:
            for line in order.order_line:
                return line.tax_id

    def _get_unit_price(self):
        for order in self:
            for line in order.order_line:
                return line.price_unit

    def calculate_days_hours(self,start,end):

        start_date = start.date()
        end_date = end.date()
        start_time = start.time()

        days = 0
        hours = 0
        if end_date > start_date:
            days = (end_date - start_date).days
            # days = end_date.day - start_date.day
            print('end_date,start_date',end_date,start_date)
        if days:
            # print('True')
            temp_end_date = datetime.datetime.combine(end_date,start_time)
            # temp_end_date = pytz.utc.localize(datetime.datetime.combine(end_date,start_time)).astimezone(tz)
        if not days:
            # print('False')
            temp_end_date = start
        if temp_end_date < end:
            # print('temp_end_date , end',temp_end_date,end)
            extra_duration =  end - temp_end_date
            # print('Extra durations==========', extra_duration)
            extra_duration_in_seconds = extra_duration.total_seconds()
            day_extra_horurs = (extra_duration_in_seconds // 3600)
            hours = day_extra_horurs

        # print('days,hours',days,hours)
        return days,hours



    def compute_amount_due(self):
        dt = datetime.datetime.now()
        actual_date = dt
        # print('yesssssssssssssssss',actual_date,dt)
        sale_obj = self.env['sale.order'].search([])
        for order in sale_obj:
            if not order.date_end:
                continue
            # print('dfdsffdsf',order.date_end)
            if order.check_out and not order.check_in:
                if order.actualy_checked:
                    count_days,count_hours = self.calculate_days_hours(order.actualy_checked,actual_date)
                order.extra_day = count_days
            if order.date_end < actual_date and order.check_out and not order.check_in :
                # print('crosssssssssssssed')

                extra_days, extra_hour = self.calculate_days_hours(order.date_end, actual_date)
                extra_days_charges = 0
                extra_hours_charges = 0
                total_extra_cost = 0
                tax_amount = 0
                total_amount_with_tax = 0
                total_cost = 0
                if extra_days:
                    extra_days_charges = extra_days * order.extra_daily_charges
                    # order.extra_day = extra_days
                if extra_hour:
                    extra_hours_charges = extra_hour * order.extra_hour_charges

                if extra_hours_charges or extra_days_charges:
                    total_extra_cost = extra_days_charges + extra_hours_charges
                if total_extra_cost:
                    tax_id = order._get_tax()
                    taxes = tax_id.compute_all(total_extra_cost)
                    total_amount_with_tax = taxes['total_included']
                    tax_amount = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                if total_amount_with_tax or order.amount_total or total_extra_cost:
                    total_cost = order.amount_total + total_amount_with_tax

                if order.amount_total or total_cost:
                    difference = round(total_cost - order.total_amount_paid)
                    if difference > 0:
                        order.remaining_amount = difference
                        order.returning_amount = 0



class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle.odometer"


    odometer_id = fields.Many2one('sale.order', string= "Fleet Odometer")



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced')
    def _compute_invoice_status(self):
        """
        Overiding Compute the invoice status of a SO line. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also hte default value if the conditions of no other status is met.
        - to invoice: we refer to the quantity to invoice of the line. Refer to method
          `_get_to_invoice_qty()` for more information on how this quantity is calculated.
        - upselling: this is possible only for a product invoiced on ordered quantities for which
          we delivered more than expected. The could arise if, for example, a project took more
          time than expected but we decided not to invoice the extra cost to the client. This
          occurs onyl in state 'sale', so that when a SO is set to done, the upselling opportunity
          is removed from the list.
        - invoiced: the quantity invoiced is larger or equal to the quantity ordered.
        Here is the Given Condition for the the Status "Invoiced" and "To Invoiced"

                      +-----------------+-----------------+-----------------+--------------+
                      | float_is_zero   | float_compare   | qty_invoiced    | Result       |
                      +-----------------+-----------------+-----------------+--------------+
                      | False           |       1         |     >0          | Invoiced     |
                      +-----------------+-----------------+-----------------+--------------+
                      | False           |       -1        |      >0         | Invoiced     |
                      +-----------------+-----------------+-----------------+--------------+
                      | True            |       0         |      >0         | Invoiced     |
                      +-----------------+-----------------+-----------------+--------------+
                      | False           |       -1        |      =0         | To Invoice   |
                      +-----------------+-----------------+-----------------+--------------+
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            print('float_is_zero THis value should not be 0',
                  float_is_zero(line.qty_to_invoice, precision_digits=precision))
            print('float_compare', float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision))
            if line.state not in ('sale', 'done'):
                line.invoice_status = 'no'
            elif line.is_downpayment and line.untaxed_amount_to_invoice == 0:
                line.invoice_status = 'invoiced'
            elif not float_is_zero(line.qty_to_invoice, precision_digits=precision) and \
                    float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) < 0 and \
                    line.qty_invoiced == 0:
                print('we are "to invoice"')
                line.invoice_status = 'to invoice'
            elif line.state == 'sale' and line.product_id.invoice_policy == 'order' and \
                    float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1:
                line.invoice_status = 'upselling'
            elif line.qty_invoiced > 0:
                print('We are "Invoiced"')
                line.invoice_status = 'invoiced'
                print(line.invoice_status)
            else:
                line.invoice_status = 'no'


   