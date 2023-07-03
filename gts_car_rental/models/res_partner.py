from odoo import fields, models,api,_
from odoo.exceptions import UserError
from datetime import date


class ResPartner(models.Model):

    _inherit = 'res.partner'

    iqama_no = fields.Char(string='IQAMA/ID No')
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', default=lambda self: self._get_default_country())
    nationality = fields.Many2one('res.country',string='Nationality',ondelete='restrict')
    iqama_expiry = fields.Date(string = 'IQAMA/Id Expiry Date')
    driver_expiry = fields.Date(string='Driving License Expiry Date')
    is_vendor = fields.Boolean(string='Is Vendor?')
    # driving_number = fields.Char(string='Driving License No')

    @api.model
    def _get_default_country(self):
        country = self.env['res.country'].search([('code', '=', 'SA')], limit=1)
        return country.id

    @api.depends('name', 'phone')
    def name_get(self):
        res = []
        for record in self:
            if self.env.context.get('partner_id', False):
                name = record.name
                if record.phone:
                    name = name + ',' + record.phone
                if record.iqama_no:
                    name = name + ',' + record.iqama_no
                res.append((record.id, name))
            else :
                name = record.name
                res.append((record.id, name))
        return res

    @api.onchange('driver_expiry')
    def onchange_driver_expiry(self):
        today = date.today()
        if self.driver_expiry:
            if self.driver_expiry < today:
                raise UserError(_("Driving License Expiry Date cannot be Less than Today's date "))


