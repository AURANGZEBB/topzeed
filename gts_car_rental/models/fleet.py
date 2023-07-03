# -*- coding: utf-8 -*-

from odoo import models, api, fields, _



class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'


    sale_amount_total = fields.Monetary(compute='_compute_sale_data', string="Sum of Orders", help="Untaxed Total of Confirmed Orders", currency_field='company_currency')
    sale_order_count = fields.Integer(compute='_compute_sale_data', string="Number of Sale Orders")
    order_ids = fields.One2many('sale.order', 'vehicle_id', string='Orders')
    company_currency = fields.Many2one("res.currency", string='Currency', related='company_id.currency_id', readonly=True)
    status = fields.Selection(
        [('checkin','Check-In'),
        ('checkout', 'Check-Out')
        ], string='Car Status', index=True, tracking=2,default='checkin')
    ar_license_plate = fields.Char(string='License Plate (Arabic)')
    registration_no = fields.Char(string='Registration no')
    ar_registration_no = fields.Char(string='Registration no (Arabic)')
    tracker = fields.Boolean(string='Tracker Install?')
    service_odometer = fields.Float(string='Odometer for Next Service')

    @api.depends('order_ids.state', 'order_ids.currency_id', 'order_ids.amount_untaxed', 'order_ids.date_order', 'order_ids.company_id','order_ids.vehicle_id','order_ids.driver_id','order_ids.date_start','order_ids.date_end','order_ids.status')
    def _compute_sale_data(self):
        for fleet in self:
            # total = 0.0
            sale_order_cnt = 0
            # company_currency = fleet.company_currency or self.env.company.currency_id
            for order in fleet.order_ids:
                if order.state in ('sale','done'):
                    sale_order_cnt += 1
                    # total += order.currency_id._convert(
                    #     order.amount_untaxed, company_currency, order.company_id, order.date_order or fields.Date.today())
            # fleet.sale_amount_total = total
            fleet.sale_order_count = sale_order_cnt



    def action_view_sale_order(self):
        action = self.env["ir.actions.actions"]._for_xml_id("car_rental.action_confirm_menu")
        action['context'] = {
            'search_default_vehicle_id' : self.id,
            'default_vehicle_id' : self.id,
            'default_car_rental_flag' : True

        }
        action['domain'] = [('vehicle_id', '=', self.id),('car_rental_flag','=',True), ('state', 'in', ('done','sale'))]
        orders = self.mapped('order_ids').filtered(lambda l: l.state  in ('done','sale'))
        if len(orders) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = orders.id
        return action

    # def _merge_get_fields_specific(self):
    #     fields_info = super(CrmLead, self)._merge_get_fields_specific()
    #     # add all the orders from all lead to merge
    #     fields_info['order_ids'] = lambda fname, leads: [(4, order.id) for order in leads.order_ids]
    #     return fields_info