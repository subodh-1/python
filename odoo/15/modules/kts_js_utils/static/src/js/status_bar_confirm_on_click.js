odoo.define('kts_js_utils.custom_stage_confirm', function (require) {
    "use strict";

    //require the module to modify:
    var relational_fields = require('web.relational_fields');

    var core = require('web.core');
    var Dialog = require('web.Dialog');

    var _t = core._t;


    //override the method:
    relational_fields.FieldStatus.include({
    	check_condition: function (modelName, record_id ,data_changed) {
            var valid = this._rpc({
                "model": modelName,
                "method": "on_cick_statusbar_stage",
                "args": [record_id ,data_changed]
            });
            return valid;
        },

        /**
         * Called when on status stage is clicked -> sets the field value.
         * @private
         * @param {MouseEvent} e
         */
        _onClickStage: function (e) {
            var workflow_stage_id=$(e.currentTarget).data("value");
            var model = this.model;
            var record = this.recordData;
            var self = this;
            self.check_condition(model, record, workflow_stage_id).then(function(opendialog){
                if(!opendialog){
                    self._setValue($(e.currentTarget).data("value"));
                }else{
                    Dialog.confirm(this, _t(opendialog), {
                                        confirm_callback: function () {
                                            self._setValue($(e.currentTarget).data("value"));
                                 },
                            });
                }
            });

        },
    });
});
