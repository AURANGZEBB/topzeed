from odoo import models,fields,api,_
import base64
import datetime
import pytz
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from decimal import Decimal

class DueAmount(models.TransientModel):
    _name = 'due.amount'

    checkin = fields.Datetime('Expected Checked-In')
    checkout = fields.Datetime('Checked-Out')
    odometer = fields.Float('Odometer Reading')
    actual_date = fields.Datetime("Expected Return Date")
    odometer_price = fields.Float('Extra Odometer Price')
    hour_cost = fields.Float('Extra Hour Price')
    day_cost = fields.Float('Extra Day Price')
    total_due_cost = fields.Float('Total Payable Amount')
    paid_amount = fields.Float('Total Paid Amount')
    total_bill = fields.Float('Total Bill')
    remaining_amount = fields.Float('Recievable Amount')
    returning_amount = fields.Float('Amount To Return')
    tax_id = fields.Many2one('account.tax' , string='Taxes')
    total_extra_charges = fields.Float('Total Extra Charges (without tax)')
    total_tax = fields.Float('Taxes')
    total_tax_included = fields.Float('Total Extra Charges (with tax)',digits=(2,0))


    def calculate_days_hours(self,start,end):
        # tz = pytz.timezone(request.context.get('tz', 'utc') or 'utc')
        # temp_date = pytz.utc.localize(start).astimezone(tz)
        # temp_end = pytz.utc.localize(end).astimezone(tz)
        start_date = start.date()
        end_date = end.date()
        start_time = start.time()
        # temp_end_date = datetime.datetime.combine(end_date,start_time)
        # print('temp_end_date',temp_end_date)
        # print('tz, temp_date, time, start',tz,temp_date,temp_date.time(),start)
        days = 0
        hours = 0
        if end_date > start_date:
            days = (end_date - start_date).days
            # days = end_date.day - start_date.day
            print('end_date,start_date',end_date,start_date)
        if days:
            print('True')
            temp_end_date = datetime.datetime.combine(end_date,start_time)
            # temp_end_date = pytz.utc.localize(datetime.datetime.combine(end_date,start_time)).astimezone(tz)
        if not days:
            print('False')
            temp_end_date = start
        if temp_end_date < end:
            print('temp_end_date , end',temp_end_date,end)
            extra_duration =  end - temp_end_date
            print('Extra durations==========', extra_duration)
            extra_duration_in_seconds = extra_duration.total_seconds()
            day_extra_horurs = (extra_duration_in_seconds // 3600)
            hours = day_extra_horurs

        print('days,hours',days,hours)
        return days,hours







    def _get_odometer_vlaue(self,sale_id):
        print('---------------->',self,sale_id)
        for line in sale_id.odometer_ids:
            return line.value


    def calculate_extra_price(self):
        # self.calculate_days_hours(self.checkin, self.actual_date)
        self.odometer_price = 0
        self.hour_cost = 0
        self.day_cost = 0
        self.total_tax = 0
        self.total_tax_included = 0
        self.remaining_amount = 0
        self.returning_amount = 0
        sale_id = self.env['sale.order'].browse(self.env.context.get('active_id'))
        actual_duration = self.actual_date - sale_id.date_start
        actual_duration_in_seconds = actual_duration.total_seconds()
        # print('insencond', actual_duration_in_seconds)
        actual_duration_in_hours = actual_duration_in_seconds // 3600
        temp_actual_duration_in_mins = actual_duration_in_seconds % 3600
        # print('tcyvbgfxdcghjbk', temp_actual_duration_in_mins)
        actual_duration_in_mins = 0.0
        if temp_actual_duration_in_mins > 1:
            actual_duration_in_mins = temp_actual_duration_in_mins / 60
        print(actual_duration_in_mins)
        if self.odometer > 0.0:
            actual_allowed_distance_per_hour = sale_id.allowed_odometer / 24
            total_distance_allowed = actual_allowed_distance_per_hour * actual_duration_in_hours + (
                        actual_allowed_distance_per_hour * (actual_duration_in_mins / 60))
            # print('(actual_allowed_distance_per_hour*(actual_allowed_distance_per_hour/60)',(actual_allowed_distance_per_hour*(actual_duration_in_mins/60)))
            # print('============',total_distance_allowed)
            checkin_odometer_reading = self._get_odometer_vlaue(sale_id)
            print('====', type(self.odometer),type(checkin_odometer_reading),checkin_odometer_reading)
            if checkin_odometer_reading:
                checkin_checkout_odometer_diff = self.odometer - checkin_odometer_reading
                if total_distance_allowed < checkin_checkout_odometer_diff:
                    # sale_id.chargable_odometer_reading = checkin_checkout_odometer_diff - total_distance_allowed
                    self.odometer_price = sale_id.extra_odometer_charges * (
                                checkin_checkout_odometer_diff - total_distance_allowed)
        if sale_id.date_end < self.actual_date:
            extra_day , extra_hours = self.calculate_days_hours(self.checkin,self.actual_date)
            if extra_day :
                self.day_cost = extra_day * sale_id.extra_daily_charges
                print('day cost',self.day_cost)
            if extra_hours :
                self.hour_cost = extra_day * sale_id.extra_hour_charges
                print('hour cost',self.hour_cost)
            # print('date_end',sale_id.date_end, self.checkin)
            # self.calculate_days_hours(self.checkin,self.actual_date)
            # if sale_id.date_end < self.actual_date:
            #     print('sale_id.date_end.days < self.actual_date.days:',sale_id.date_end.time(),self.actual_date.date())
            # extra_duration = self.actual_date - sale_id.date_end
            # # print('Extra days==========',extra_duration.days)
            # extra_duration_in_seconds = extra_duration.total_seconds()
            # day_extra_horurs = (extra_duration_in_seconds // 3600) / 24
            # # print(day_extra_horurs)
            # if extra_duration:
            #     extra_days = extra_duration.days
            #     extra_hours = Decimal(day_extra_horurs) % 1
            #     self.hour_cost = float(extra_hours) * sale_id.extra_hour_charges
            #     self.day_cost = extra_duration.days * sale_id.extra_daily_charges


            # print("------------------->",extra_duration.days, extra_duration.total_seconds() // 3600, Decimal(day_extra_horurs) % 1 )
            # extra_duration_in_hours = extra_duration_in_seconds // 3600
            # # sale_id.chargable_extra_hours = extra_duration_in_hours
            # self.hour_cost = extra_duration_in_hours * sale_id.extra_hour_charges

        if self.hour_cost or self.odometer_price or self.day_cost:
            self.total_extra_charges = self.hour_cost + self.odometer_price + self.day_cost
        if self.total_extra_charges:
            taxes = self.tax_id.compute_all(self.total_extra_charges)
            self.total_tax_included = taxes['total_included']
            self.total_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
        if self.total_tax_included or self.total_bill or self.total_extra_charges:
            self.total_due_cost = self.total_bill + self.total_tax_included
        if self.hour_cost or self.odometer_price or self.day_cost:
            sale_id.total_extra_price_without_taxes = self.hour_cost + self.odometer_price + self.day_cost
            sale_id.total_taxes = self.total_tax
            sale_id.total_extra_price_with_taxes = self.total_tax_included
            print('total_extra_price_with_taxes',self.total_tax_included)
        if self.paid_amount:
            self.returning_amount = 0
            self.remaining_amount = 0
            total_payable = self.total_due_cost
            difference = total_payable - self.paid_amount
            if difference > 0:
                self.remaining_amount = difference
                sale_id.remaining_amount = difference
                sale_id.returning_amount = 0
            if difference < 0:
                self.returning_amount = -difference
                sale_id.returning_amount = -difference
                sale_id.remaining_amount = 0


        return {
            'view_mode': 'form',
            'view_id': False,
            'res_model': self._name,
            'domain': [],
            'context': dict(self._context, active_ids=self.ids),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
        }
