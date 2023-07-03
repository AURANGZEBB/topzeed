import io
import base64
import json
# import xlwt

from odoo.addons.web.controllers.main import _serialize_exception
from odoo.tools import html_escape

from odoo.tools import html2plaintext, html_escape

from odoo import http
from odoo.http import request

class AccountHierarchy(http.Controller):

    @http.route('/account_hierarchy/<string:output_report_format>/<string:report_name>/<int:active_id>', type='http', auth='user')
    def account_hierarchy_report(self, output_report_format, report_name, active_id=False, **kw):
        account_hierarchy_env = request.env['account.hierarchy'].sudo().browse(active_id)
        try:
            if output_report_format == 'pdf':
                request_response = request.make_response(
                    account_hierarchy_env.with_context(active_id=active_id).print_pdf_report(),
                    headers=[
                        ('Content-Type', 'application/pdf'),
                        ('Content-Disposition', 'attachment; filename=' + 'account_hierarchy' + '.pdf;')
                    ]
                )
                return request_response
            
            if output_report_format == 'xls':
                request_response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', 'attachment; filename=Account_Hiearchy.xls')
                    ]
                )
                account_hierarchy_env.with_context(active_id=active_id).print_xls_report(request_response)
                return request_response
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))
    