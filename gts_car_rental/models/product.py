
from odoo import fields,models,api,_

class Product(models.Model):

    _inherit = 'product.template'

    is_car_rental = fields.Boolean('Is Car Rental')
    allowed_odometer = fields.Float(string='Daily Allowed KM',help= 'Allowed Distance to Travel By Car on daily basis')
    extra_hour_charges = fields.Float(string='Extra Hour Charges',help='Extra Chageres for the Car after Booked Duration')
    extra_odometer_charges = fields.Float(string='Extra Odometer Charges',help='Extra Chageres for the Car after Allowed Odometer Rating')
    extra_daily_charges = fields.Float(string='Extra Daily Chageres', help='Extra Chageres for the Car after Booked Duration.')