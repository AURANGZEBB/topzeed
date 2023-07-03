from odoo import models,fields,api,_
import base64
import datetime
from odoo.exceptions import AccessError, UserError, ValidationError

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF



class DocumentAttachment(models.TransientModel):

    _name = 'document.attachment'


    attachment_ids = fields.Many2many('ir.attachment', string='Attachment',required=True)
    document = fields.Binary('Checklist',attachment=True)
    checkout = fields.Boolean('Checkout',default=False)
    checkin = fields.Boolean('Checkin',default=False)
    actual_date = fields.Datetime('Cheked-in/Checked-out Date')
    odometer_reading = fields.Float('Odometer Reading')
    amount_paid = fields.Float('Aomunt Paid')
    tax_id = fields.Many2one('account.tax' , string='Taxes',compute='_compute_tax_id')
    total_bill = fields.Float('Total Bill')


    @api.depends('checkin')
    def _compute_tax_id(self):
        sale_id = self.env['sale.order'].browse(self.env.context.get('active_id'))
        for line in sale_id.order_line:
            self.tax_id = line.tax_id


    # encoded = base64.b64encode(document)

    # def conversion(sec):
    #     sec_value = sec % (24 * 3600)
    #     hour_value = sec_value // 3600  default=fields.Datetime.now()
    #     sec_value %= 3600
    #     min = sec_value // 60
    #     sec_value %= 60
    #     print("Converted sec value in hour:", hour_value)
    #     print("Converted sec value in minutes:", min)



    def _get_odometer_vlaue(self,sale_id):

        for line in sale_id.odometer_ids:
            return line.value

    def _get_unit_price(self,sale_id):
        for line in sale_id.order_line:
            return line.price_unit

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


    def action_confirm(self):
        sale_id = self.env['sale.order'].browse(self.env.context.get('active_id'))
        # print('booking status',sale_id.vehicle_id.status)

        if self.checkin:
            name = sale_id.name+'_'+'checkin'
        if self.checkout:
            name = sale_id.name + '_' + 'checkout'
        for attachment in self.attachment_ids:
            attachment= self.env['ir.attachment'].create({
                        'name': name,
                        'res_model': 'sale.order',
                      #  'res_field': sale_id.name,
                        # 'store_fname': sale_id.name,
                        'res_id': sale_id.id,
                        'type': 'binary',
                        'datas': attachment.datas,
                        # 'mimetype': 'application/x-pdf'
                    })
        sale_id.with_user(self.env.user).message_post(attachment_ids= [id for id in self.attachment_ids.ids] or None,)
        if self.checkin:
            if sale_id.date_end < self.actual_date:
                odometer = self._get_odometer_vlaue(sale_id)
                if odometer > self.odometer_reading:
                    raise UserError(_("Check-In Odometer reading must not be less than Check-Out Odometer reading"))
                sale_id.check_in = True
                sale_id.status = 'checkin'
                sale_id.vehicle_id.status = 'checkin'
                sale_id.actualy_checkin = self.actual_date
                vals = {
                    'date' : datetime.date.today(),
                    'vehicle_id': sale_id.vehicle_id.id,
                    'driver_id' : sale_id.driver_id.id,
                    'unit':sale_id.vehicle_id.odometer_unit,
                    'value':self.odometer_reading
                }
                sale_id.write({"odometer_ids": [(0, 0, vals)]})

                extra_days, extra_hour = self.calculate_days_hours(sale_id.date_end , self.actual_date)
                print('extra_days,extra_hours',extra_days,extra_hour)
                total_allowed_distance = sale_id.service_day * sale_id.allowed_odometer + sale_id.allowed_odometer * extra_days
                checkout_distance = self._get_odometer_vlaue(sale_id)
                print('vtotal_allowed_distance',total_allowed_distance)
                print('checkout_distance',checkout_distance)
                extra_odometer_charges = 0
                extra_days_charges = 0
                extra_hours_charges = 0
                total_extra_cost = 0
                tax_amount = 0
                total_amount_with_tax = 0
                total_cost = 0
                if total_allowed_distance < checkout_distance:
                    total_distance = self.odometer_reading - checkout_distance
                    extra_odometer = total_distance - total_allowed_distance
                    if extra_odometer > 0:
                        print('=========',extra_odometer)
                        sale_id.chargable_odometer_reading = extra_odometer
                        extra_odometer_charges = extra_odometer * sale_id.extra_odometer_charges
                if extra_days:
                    extra_days_charges = extra_days * sale_id.extra_daily_charges
                    print('extra_days_charges',extra_days_charges)
                if extra_hour:
                    extra_hours_charges = extra_hour * sale_id.extra_hour_charges
                    print('extra_hours_charges',extra_hours_charges)

                if extra_hours_charges or extra_days_charges or extra_odometer_charges:
                    sale_id.chargable_extra_hours = 24*extra_days + extra_hour
                    total_extra_cost = extra_odometer_charges + extra_days_charges + extra_hours_charges
                    print('total_extra_cost',total_extra_cost)
                if total_extra_cost:
                    taxes = self.tax_id.compute_all(total_extra_cost)
                    total_amount_with_tax = taxes['total_included']
                    print('total_amount_with_tax',total_amount_with_tax)
                    tax_amount = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                if total_amount_with_tax or self.total_bill or total_extra_cost:
                    total_cost = self.total_bill + total_amount_with_tax
                if extra_hours_charges or extra_days_charges or extra_odometer_charges:
                    sale_id.total_odometer_cost = extra_odometer_charges
                    sale_id.total_hours_cost = extra_hours_charges + extra_days_charges
                if extra_hours_charges or extra_days_charges or extra_odometer_charges:
                    sale_id.total_extra_price_without_taxes = extra_odometer_charges + extra_days_charges + extra_hours_charges
                    sale_id.total_taxes = tax_amount
                    sale_id.total_extra_price_with_taxes = total_amount_with_tax
                    sale_id.total_hours_cost = extra_hours_charges + extra_days_charges
                    sale_id.total_odometer_cost = extra_odometer_charges
                    sale_id.invoice_amount = total_cost
                if self.amount_paid or self.total_bill:
                    difference = round(total_cost - self.amount_paid)
                    if difference > 0:
                        sale_id.remaining_amount = difference
                        sale_id.returning_amount = 0
                    if difference < 0:
                        sale_id.returning_amount = -difference
                        sale_id.remaining_amount = 0


            if sale_id.date_end > self.actual_date:
                odometer = self._get_odometer_vlaue(sale_id)
                if odometer > self.odometer_reading:
                    raise UserError(_("Check-In Odometer reading must not be less than Check-Out Odometer reading"))
                sale_id.check_in = True
                sale_id.status = 'checkin'
                sale_id.vehicle_id.status = 'checkin'
                sale_id.actualy_checkin = self.actual_date
                vals = {
                    'date': datetime.date.today(),
                    'vehicle_id': sale_id.vehicle_id.id,
                    'driver_id': sale_id.driver_id.id,
                    'unit': sale_id.vehicle_id.odometer_unit,
                    'value': self.odometer_reading
                }
                sale_id.write({"odometer_ids": [(0, 0, vals)]})
                less_days, less_hour = self.calculate_days_hours(self.actual_date, sale_id.date_end)
                total_allowed_distance = sale_id.service_day * sale_id.allowed_odometer - sale_id.allowed_odometer * less_days
                checkout_distance = self._get_odometer_vlaue(sale_id)
                extra_odometer_charges = 0
                service_bill = 0
                service_tax = 0
                total_cost = 0
                if total_allowed_distance < checkout_distance:
                    total_distance = self.odometer_reading - checkout_distance
                    extra_odometer = total_distance - total_allowed_distance
                    if extra_odometer > 0:
                        extra_odometer_charges = extra_odometer * sale_id.extra_odometer_charges

                service_days,service_hour = self.calculate_days_hours(sale_id.date_start,self.actual_date)
                unit_price = self._get_unit_price(sale_id)
                if unit_price and service_days:
                    service_bill = unit_price * service_days
                if extra_odometer_charges:
                    service_bill += extra_odometer_charges
                    sale_id.total_odometer_cost = extra_odometer_charges
                if self.tax_id:
                    taxes = self.tax_id.compute_all(service_bill)
                    total_cost = taxes['total_included']
                    service_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                if self.amount_paid or self.total_bill:
                    difference = round(self.amount_paid - total_cost)
                    if difference > 0:
                        sale_id.returning_amount = difference
                        sale_id.invoice_amount = total_cost
                        sale_id.remaining_amount = 0
                    if difference < 0:
                        sale_id.returning_amount = 0
                        sale_id.remaining_amount = -difference
                        sale_id.invoice_amount = total_cost



        if self.checkout:
            if self.odometer_reading < 0 or self.odometer_reading == 0:
                raise UserError(_("Please enter Odometer reading"))

            if sale_id.vehicle_id.status == 'checkout':
                raise UserError(_('The "{vehicle}" is already checked out in another booking.\n Please Checkin Vehicle First !'.format(vehicle=sale_id.vehicle_id.name)))
            elif sale_id.vehicle_id.status == 'checkin':
                sale_id.vehicle_id.status = 'checkout'

            sale_id.status = 'checkout'
            sale_id.check_out = True
            sale_id.actualy_checked = self.actual_date
            vals = {
                'date': datetime.date.today(),
                'vehicle_id': sale_id.vehicle_id.id,
                'driver_id': sale_id.driver_id.id,
                'unit': sale_id.vehicle_id.odometer_unit,
                'value': self.odometer_reading
            }
            sale_id.write({"odometer_ids": [(0, 0, vals)]})
        # if self.checkout and sale_id.vehicle_id.status == 'checkout':
        #     raise UserError(_('The "{vehicle}" is already checked out in another booking.\n Please Checkin Vehicle First !'.format(vehicle=sale_id.vehicle_id.name)))
