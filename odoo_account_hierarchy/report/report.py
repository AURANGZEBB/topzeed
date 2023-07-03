from odoo import models, fields, api,_

class ReportAccountHierarchy(models.AbstractModel):
    _name = 'report.odoo_account_hierarchy.report_account_hierarchy_wizard'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'company_name': data['company_name'],
            'lines': data['lines'],
        }
    