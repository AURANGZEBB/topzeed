odoo.define('odoo_account_hierarchy.AccountHierarchyBackend', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var session = require('web.session');
    var AccountHierarchyWidget = require('odoo_account_hierarchy.AccountHierarchyWidget');
    var framework = require('web.framework');

    var QWeb = core.qweb;

    var account_hierarchy = AbstractAction.extend({
        hasControlPanel: true,

        // Stores all the parameters of the action.
        init: function(parent, action) {
            this._super.apply(this, arguments);
            this.given_context = action.context;
            if (action.context.context) {
                this.given_context = action.context.context;
            }
            this.controller_url = action.context.url;
        },

        willStart: function() {
            return Promise.all([this._super.apply(this, arguments), this.get_html()]);
        },

        set_html: function() {
            var self = this;
            var def = Promise.resolve();
            if (!this.account_hierarchy_widget) {
                this.account_hierarchy_widget = new AccountHierarchyWidget(this, this.given_context);
                def = this.account_hierarchy_widget.appendTo(this.$('.o_content'));
            }
            return def.then(function () {
                self.account_hierarchy_widget.$el.html(self.html);
                if (self.given_context.auto_unfold) {
                    _.each(self.$el.find('.fa-caret-right'), function (line) {                    
                        self.account_hierarchy_widget.autounfold(line);
                    });
                }
            });
        },

        start: async function() {
            QWeb.add_template("/odoo_account_hierarchy/static/src/xml/account_hierarchy_backend.xml");
            this.controlPanelProps.cp_content = { $buttons: this.$buttons };
            await this._super(...arguments);
            this.set_html();
        },

        // Fetches the html and is previous hierarchy report.context if any, else create it
        get_html: async function() {
            const { html } = await this._rpc({
                args: [this.given_context],
                method: 'get_html',
                model: 'account.hierarchy',
            });
            this.html = html;
            this.renderButtons();
        },

        update_cp: function() {
            if (!this.$buttons) {
                this.renderButtons();
            }
            this.controlPanelProps.cp_content = { $buttons: this.$buttons };
            return this.updateControlPanel();
        },

        renderButtons: function() {
            var self = this;
            this.$buttons = $(QWeb.render("accountHiearchy.buttons", {widget: this}));
            this.$buttons.bind('click', function () {  
                console.log("==self", self);
                if(this.id == "expand_hierarchy"){
                    self._onExpandHierarchy();
                }
                if(this.id == "collapse_hierarchy"){
                    self._onCollapseHierarchy();
                }
                if (this.id == "print_hierarchy_pdf"){
                    framework.blockUI();
                    var active_id = self.given_context.active_id;
                    var url = self.controller_url.replace('active_id', active_id);                        
                    session.get_file({
                        url: url.replace('output_report_format', 'pdf'),
                        complete: framework.unblockUI,
                        error: (e) => self.call('crash_manager', 'rpc_error', e),
                    });
                }
                if (this.id == "print_hierarchy_xls"){
                    framework.blockUI();
                    var active_id = self.given_context.active_id;
                    var url = self.controller_url.replace('active_id', active_id);                        
                    session.get_file({
                        url: url.replace('output_report_format', 'xls'),
                        complete: framework.unblockUI,
                        error: (e) => self.call('crash_manager', 'rpc_error', e),
                    });
                }

            })
        },

        _onExpandHierarchy: function(){
            var self = this;
            _.each(self.$el.find('.fa-caret-right'), function (line) {                    
                self.account_hierarchy_widget.autounfold(line);
            });
        },

        _onCollapseHierarchy: function(){
            var self = this;
            _.each(self.$el.find('.fa-caret-down'), function (line) {                    
                self.account_hierarchy_widget.autofold(line);
            });
        },

        do_show: function() {
            this._super();
            this.update_cp();
        },
    });

    core.action_registry.add("account_hierarchy", account_hierarchy);
    return account_hierarchy;
});