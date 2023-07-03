odoo.define('odoo_account_hierarchy.AccountHierarchyWidget', function (require) {
    'use strict';

    var core = require('web.core');
    var Widget = require('web.Widget');

    var QWeb = core.qweb;
    var _t = core._t;

    var AccountHierarchyWidget = Widget.extend({
        events: {
            'click span.accounts_hierarchy_foldable': 'fold',
            'click span.accounts_hierarchy_unfoldable': 'unfold',
            'click span.accounts_hierarchy_action': 'boundLink',
        },

        init: function(parent) {
            this._super.apply(this, arguments);
        },

        start: function() {
            QWeb.add_template("/odoo_account_hierarchy/static/src/xml/account_hierarchy_lines.xml");
            return this._super.apply(this, arguments);
        },
        
        boundLink: function(e) {
            e.preventDefault();
            var self = this            
            var id = $(e.currentTarget).data('id');
            var active_id = $(e.currentTarget).data('active_id');
            return this._rpc({
                model: 'account.hierarchy',
                method: 'get_child_ids',
                args: [parseInt(active_id, 10), parseInt(id, 10)],
            }).then(function (result) {
                if (result){
                    return self.do_action({
                        name: 'Journal Items',
                        type: 'ir.actions.act_window',
                        res_model: 'account.move.line',
                        domain: result,
                        views: [[false, 'list'], [false, 'form']],
                        view_mode: "list",
                        target: 'current'
                    });
                }            
            });
        },

        removeLine: function(element) {
            var self = this;
            var el, $el;
            var id = element.data('id');
            var $accountEl = element.nextAll('tr[data-parent_id=' + id + ']')
            for (el in $accountEl) {
                $el = $($accountEl[el]).find(".account_hierarchy_report_line_domain_0, .account_hierarchy_report_line_domain_1");
                if ($el.length === 0) {
                    break;
                }                
                else {
                    var $nextEls = $($el[0]).parents("tr");
                    self.removeLine($nextEls);
                    $nextEls.remove();
                }
                $el.remove();
            }
            return true;
        },

        fold: function(e) {            
            this.removeLine($(e.target).parents('tr'));
            var id = $(e.target).parents('tr').find('td.accounts_hierarchy_report_line_td').data('id');    
            $(e.target).parents('tr').find('span.accounts_hierarchy_foldable').replaceWith(QWeb.render("unfoldable", {lineId: id}));
            $(e.target).parents('tr').toggleClass('o_accounts_hierarchy_unfolded');
        },

        autounfold: function(target) {
            var self = this;
            var $CurretElement;
            $CurretElement = $(target).parents('tr').find('td.accounts_hierarchy_report_line_td');

            var id = $CurretElement.data('id');
            var active_id = $CurretElement.data('active_id');
            var active_model_id = $CurretElement.data('model_id');
            var row_level = $CurretElement.data('level');
            var $cursor = $(target).parents('tr');

            this._rpc({
                    model: 'account.hierarchy',
                    method: 'get_lines',
                    args: [parseInt(active_id, 10), parseInt(id, 10)],
                    kwargs: {
                        'model_id': active_model_id,
                        'level': parseInt(row_level) + 1 || 1
                    },
                })
                .then(function (lines) {
                    _.each(lines, function (line) {
                        $cursor.after(QWeb.render("account_heirarchy_report_lines", {l: line}));
                        $cursor = $cursor.next();
                        if ($cursor.find('span.accounts_hierarchy_unfoldable')){
                            self.autounfold($cursor.find(".fa-caret-right"));
                        }
                    })
                });            
            $(target).parents('tr').find('span.accounts_hierarchy_unfoldable').replaceWith(QWeb.render("foldable", {lineId: id}));
            $(target).parents('tr').toggleClass('o_accounts_hierarchy_unfolded');
        },

        unfold: function(e) {            
            var $CurretElement;
            $CurretElement = $(e.target).parents('tr').find('td.accounts_hierarchy_report_line_td');
            var id = $CurretElement.data('id');
            var active_id = $CurretElement.data('active_id');
            var active_model_id = $CurretElement.data('model_id');
            var row_level = $CurretElement.data('level');
            var $cursor = $(e.target).parents('tr');
            this._rpc({
                    model: 'account.hierarchy',
                    method: 'get_lines',
                    args: [parseInt(active_id, 10), parseInt(id, 10)],
                    kwargs: {
                        'model_id': active_model_id,
                        'level': parseInt(row_level) + 1 || 1
                    },
                })
                .then(function (lines) {
                    _.each(lines, function (line) {                        
                        $cursor.after(QWeb.render("account_heirarchy_report_lines", {l: line}));
                        $cursor = $cursor.next();                        
                    });
                });
            $(e.target).parents('tr').find('span.accounts_hierarchy_unfoldable').replaceWith(QWeb.render("foldable", {lineId: id}));
            $(e.target).parents('tr').toggleClass('o_accounts_hierarchy_unfolded');
        },

        autofold: function(target) {
            var self = this;
            var $CurretElement;
            $CurretElement = $(target).parents('tr').find('td.accounts_hierarchy_report_line_td');
            var id = $CurretElement.data('id');
            var $accountEl = $(target).parents('tr').nextAll('tr[data-parent_id=' + id + ']')                
            var el, $el;
            for (el in $accountEl) {
                $el = $($accountEl[el]).find(".account_hierarchy_report_line_domain_0, .account_hierarchy_report_line_domain_1");
                if ($el.length === 0) {
                    break;
                }                        
                else {
                    var $nextEls = $($el[0]).parents("tr");
                    self.autofold($nextEls.find(".fa-caret-down"));
                    $nextEls.remove();
                }
                $el.remove();
            }
            $(target).parents('tr').find('span.accounts_hierarchy_foldable').replaceWith(QWeb.render("unfoldable", {lineId: id}));
            $(target).parents('tr').toggleClass('o_accounts_hierarchy_unfolded');
        }
        
    });

    return AccountHierarchyWidget;
});