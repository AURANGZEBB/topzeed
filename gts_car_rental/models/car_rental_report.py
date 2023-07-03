from odoo import api, fields, models, tools, _
from datetime import datetime, timedelta
import datetime

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ## function to fetch the current date record and template creation.
    def daily_booking_report(self):
        body_header = """
                        <p>Dear Team,</p><br/>
                        <p>Kindly find the Today's Bookings and Payment Details</p><br/><br/>
                        <div style="border-spacing: 0;border-collapse: collapse;color: #222;direction: ltr;font: small/ 1.5  Arial,Helvetica,sans-serif;height: 100px;width: 200px;border-radius: 10px;box-sizing: border-box;border: solid 1px black;background-color: #e9dccc;display: inline-block;margin: 12px;">
                            <p style="text-align:center; color:#A52A2A;font-size:15px;margin-top: 10px;"><b> Total Booking </b></p>

                """
        template = self.env.ref('car_rental.booking_email_template')
        users_list = self.env['res.users'].search([])
        saleorder_obj = self.env['sale.order'].search([])
        start_time = datetime.datetime.combine(fields.Date.today(), datetime.time(0, 0, 0))
        end_time = datetime.datetime.combine(fields.Date.today(), datetime.time(23, 59, 59))
        booking_domain = [('state', 'in', ('sale', 'done')),('date_order', '>=', start_time),('date_order','<=',end_time)]
        draft_domain = [('state', 'in', ('sale', 'draft')),('date_order', '>=', start_time),('date_order','<=',end_time)]
        booking_obj = saleorder_obj.search(booking_domain)
        draft_obj = saleorder_obj.search(draft_domain)
        booking_count = saleorder_obj.search_count(booking_domain)
        draft_count = saleorder_obj.search_count(draft_domain)

        body_header_draft = """
                            </br>
                            </br>
                            <h2>Draft Booking</h2>
                            <table style="width: 100%; border: 1px solid;border-collapse:collapse">
                            <tbody>
                            <tr style="border: 1px solid; background-color: #FAEBD7;">
                            <td align="center" style="border: 1px solid"><b>Order No</b></td>
                            <td align="center" style="border: 1px solid"><b>Vehicle</b></td>
                            <td align="center" style="border: 1px solid"><b>Customer</b></td>
                            <td align="center" style="border: 1px solid"><b>Booking From</b></td>
                            <td align="center" style="border: 1px solid"><b>Booking Till</b></td>
                            </tr>
                        """
        for draft in draft_obj:
            if draft:
                body_header_draft += """<tr style="border: 1px solid">
                                                   <td align="center" style="border: 1px solid">{order}</td>
                                                   <td align="center" style="border: 1px solid">{vehicle}</td>
                                                   <td align="center" style="border: 1px solid">{customer}</td>
                                                   <td align="center" style="border: 1px solid">{checkout}</td>
                                                   <td align="center" style="border: 1px solid">{checkin}</td>
                                                    </tr>""".format(
                                                        order = draft.name,
                                                        vehicle = draft.vehicle_id.license_plate + draft.vehicle_id.model_id.name,
                                                        customer = draft.partner_id.name,
                                                        checkout = draft.date_start,
                                                        checkin = draft.date_end
                                                    )

        body_header_draft += "</tbody></table>"


        body_header_booking = """
                            </br>
                            </br>
                            <h2>Confirmed Booking</h2>
                            <table style="width: 100%; border: 1px solid;border-collapse:collapse">
                            <tbody>
                            <tr style="border: 1px solid; background-color: #FAEBD7;">
                            <td align="center" style="border: 1px solid"><b>Order No</b></td>
                            <td align="center" style="border: 1px solid"><b>Vehicle</b></td>
                            <td align="center" style="border: 1px solid"><b>Customer</b></td>
                            <td align="center" style="border: 1px solid"><b>Booking From</b></td>
                            <td align="center" style="border: 1px solid"><b>Booking Till</b></td>
                            </tr>
                        """
        for booking in booking_obj:
            if booking:
                body_header_booking += """<tr style="border: 1px solid">
                                                   <td align="center" style="border: 1px solid">{order}</td>
                                                   <td align="center" style="border: 1px solid">{vehicle}</td>
                                                   <td align="center" style="border: 1px solid">{customer}</td>
                                                   <td align="center" style="border: 1px solid">{checkout}</td>
                                                   <td align="center" style="border: 1px solid">{checkin}</td>
                                                    </tr>""".format(
                                                        order = booking.name,
                                                        vehicle = booking.vehicle_id.license_plate + booking.vehicle_id.model_id.name,
                                                        customer = booking.partner_id.name,
                                                        checkout = booking.date_start,
                                                        checkin = booking.date_end
                                                    )

        body_header_booking += "</tbody></table>"

        check_domain = [('state', 'in', ('sale', 'done')),('actualy_checked','>=',start_time),('actualy_checked','<=',end_time),'|',
                        ('actualy_checkin','>=',start_time),('actualy_checkin','<=',end_time)]
        check_out_in_obj = saleorder_obj.search(check_domain)
        check_out_domain = [('state', 'in', ('sale', 'done')),('actualy_checked','>=',start_time),('actualy_checked','<=',end_time)]
        check_in_domain = [('state', 'in', ('sale', 'done')),('actualy_checkin','>=',start_time),('actualy_checkin','<=',end_time)]
        check_out_count = saleorder_obj.search_count(check_out_domain)
        check_in_count = saleorder_obj.search_count(check_in_domain)
        check_out_obj = saleorder_obj.search(check_out_domain)
        check_in_obj = saleorder_obj.search(check_in_domain)
        body_header_checkout = """
                                    </br>                                    
                                    </br>
                                    <h2>Checked Out</h2>
                                    <table style="width: 100%; border: 1px solid;border-collapse:collapse">
                                    <tbody>
                                    <tr style="border: 1px solid; background-color: #FAEBD7;">
                                    <td align="center" style="border: 1px solid"><b>Order No</b></td>
                                    <td align="center" style="border: 1px solid"><b>Vehicle</b></td>
                                    <td align="center" style="border: 1px solid"><b>Customer</b></td>
                                    <td align="center" style="border: 1px solid"><b>CheckOut Date</b></td>
                                    </tr>
                                """
        for check in check_out_obj:
            if check:
                body_header_checkout += """<tr style="border: 1px solid">
                                                                   <td align="left" style="border: 1px solid">{order}</td>
                                                                   <td align="center" style="border: 1px solid">{vehicle}</td>
                                                                   <td align="center" style="border: 1px solid">{customer}</td>
                                                                   <td align="center" style="border: 1px solid">{checkout}</td>
                                                                    </tr>""".format(
                    order=check.name,
                    vehicle=check.vehicle_id.license_plate + check.vehicle_id.model_id.name,
                    customer=check.partner_id.name,
                    checkout=check.actualy_checked,
                )
        body_header_checkout += "</tbody></table>"

        body_header_checkin = """
                                    </br>                                    
                                    </br>
                                    <h2>Checked In</h2>
                                    <table style="width: 100%; border: 1px solid;border-collapse:collapse">
                                    <tbody>
                                    <tr style="border: 1px solid; background-color: #FAEBD7;">
                                    <td align="center" style="border: 1px solid"><b>Order No</b></td>
                                    <td align="center" style="border: 1px solid"><b>Vehicle</b></td>
                                    <td align="center" style="border: 1px solid"><b>Customer</b></td>
                                    <td align="center" style="border: 1px solid"><b>CheckIn Date</b></td>
                                    </tr>
                                """
        for check in check_in_obj:
            if check:
                body_header_checkin += """<tr style="border: 1px solid">
                                                                   <td align="left" style="border: 1px solid">{order}</td>
                                                                   <td align="center" style="border: 1px solid">{vehicle}</td>
                                                                   <td align="center" style="border: 1px solid">{customer}</td>
                                                                   <td align="center" style="border: 1px solid">{checkin}</td>
                                                                    </tr>""".format(
                    order=check.name,
                    vehicle=check.vehicle_id.license_plate + check.vehicle_id.model_id.name,
                    customer=check.partner_id.name,
                    checkin=check.actualy_checkin
                )
        body_header_checkin += "</tbody></table>"

        account_payment_obj = self.env['account.payment']
        today = fields.Date.today()
        domain = [('date','=',today)]
        payment_obj = account_payment_obj.search(domain)
        body_header_payment = """
                            </br>
                            </br>
                            <h2>Payments</h2>
                                <table style="width: 100%; border: 1px solid;border-collapse:collapse">
                                <tbody>
                                <tr style="border: 1px solid; background-color: #FAEBD7;">
                                <td align="center" style="border: 1px solid"><b>Ref No</b></td>
                                <td align="center" style="border: 1px solid"><b>Amount</b></td>
                                <td align="center" style="border: 1px solid"><b>Customer</b></td>
                                <td align="center" style="border: 1px solid"><b>Nature</b></td>
                                </tr>
                            """
        receive_amount = 0.0
        return_amount = 0.0
        for payment in payment_obj:
            if payment:
                if payment.payment_type == 'inbound':
                    receive_amount += payment.amount
                    nature = 'Received'
                if payment.payment_type == 'outbound':
                    return_amount += payment.amount
                    nature = 'Returned'
                body_header_payment += """<tr style="border: 1px solid">
                                       <td align="left" style="border: 1px solid">{ref}</td>
                                       <td align="center" style="border: 1px solid">{amount}</td>
                                       <td align="center" style="border: 1px solid">{customer}</td>
                                       <td align="center" style="border: 1px solid">{nature}</td>
                                        </tr>""".format(
                    ref=payment.ref,
                    amount=payment.amount,
                    customer=payment.partner_id.name,
                    nature=nature,
                )
        body_header_payment += "</tbody></table>"

        body_header += """
                                        <p style="text-align : center;color:#A52A2A;font-size:25px;margin-top: 10px; "><b>{total_booking}</b>
                                """.format(total_booking=booking_count)
        body_header += """</div>"""
        body_header += """
                                <div style="border-spacing: 0;border-collapse: collapse;color: #222;direction: ltr;font: small/ 1.5  Arial,Helvetica,sans-serif;height: 100px;width: 200px;border-radius: 10px;box-sizing: border-box;border: solid 1px black;background-color: #e9dccc;display: inline-block;margin: 12px;">
                                    <p style="text-align:center; color:#A52A2A;font-size:15px;margin-top: 10px;"><b> Total Checkout </b></p>
                        """
        body_header += """
                                        <p style="text-align : center;color:#A52A2A;font-size:25px;margin-top: 10px;"><b>{total_checkout_count}</b>
                                        """.format(total_checkout_count=check_out_count)
        body_header += """</div>"""
        body_header += """
                                <div style="border-spacing: 0;border-collapse: collapse;color: #222;direction: ltr;font: small/ 1.5  Arial,Helvetica,sans-serif;height: 100px;width: 200px;border-radius: 10px;box-sizing: border-box;border: solid 1px black;background-color: #e9dccc;display: inline-block;margin: 12px;">
                                    <p style="text-align:center; color:#A52A2A;font-size:15px;margin-top: 10px;"><b> Total Checkin </b></p>
                                """
        body_header += """
                                    <p style="text-align : center;color:#A52A2A;font-size:25px;margin-top: 10px;"><b>{total_checkin_count}</b>
                                    """.format(total_checkin_count=check_in_count)
        body_header += """</div>"""

        body_header += """
                                <div style="border-spacing: 0;border-collapse: collapse;color: #222;direction: ltr;font: small/ 1.5  Arial,Helvetica,sans-serif;height: 100px;width: 200px;border-radius: 10px;box-sizing: border-box;border: solid 1px black;background-color: #e9dccc;display: inline-block;margin: 12px;">
                                    <p style="text-align:center; color:#A52A2A;font-size:15px;margin-top: 10px;"><b>Total Payment Received </b></p>
                                """
        body_header += """
                                <p style="text-align : center;color:#A52A2A;font-size:25px;margin-top: 10px;"><b>{total_payment_received}</b>
                                """.format(total_payment_received=receive_amount)
        body_header += """</div>"""
        body_header += """
                                <div style="border-spacing: 0;border-collapse: collapse;color: #222;direction: ltr;font: small/ 1.5  Arial,Helvetica,sans-serif;height: 100px;width: 200px;border-radius: 10px;box-sizing: border-box;border: solid 1px black;background-color: #e9dccc;display: inline-block;margin: 12px;">
                                    <p style="text-align:center; color:#A52A2A;font-size:15px;margin-top: 10px;"><b> Total Payment Returned </b></p>
                                """
        body_header += """
                                    <p style="text-align : center;color:#A52A2A;font-size:25px;margin-top: 10px;"><b>{total_payment_return}</b>
                                    """.format(total_payment_return=return_amount)
        body_header += """</div>"""
        body_header += """</div><br></br>"""






        for group_user in users_list:
            # if group_user.has_group('account.group_account_manager'):account.group_account_manager
            if group_user.has_group('account.group_account_manager'):
                if template:
                    template.email_from = 'alreba_carrental@gmail.com'
                    template.email_to = group_user.login
                    template['body_html'] = body_header + ' ' + body_header_draft + ' ' + body_header_booking + ' ' + body_header_checkout + ' ' + body_header_checkin + ' '  + body_header_payment
                    # template['body_html'] = body_header_booking
                    template.send_mail(self.id, force_send=True)
