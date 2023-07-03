from odoo import models,fields,api,_
import base64
import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF



class TammAuthorization(models.TransientModel):

    _name = 'tamm.authorization'

    tamm_autho = fields.Boolean('Tamm Authorization')

    def action_autho(self):
        sale_id = self.env['sale.order'].browse(self.env.context.get('active_id'))
        sale_id.tamm_authorization = self.tamm_autho
