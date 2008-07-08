/* ************************************************************************

   qooxdoo - the new era of web development

   http://qooxdoo.org

   Copyright:
     2004-2008 1&1 Internet AG, Germany, http://www.1und1.de

   License:
     LGPL: http://www.gnu.org/licenses/lgpl.html
     EPL: http://www.eclipse.org/org/documents/epl-v10.php
     See the LICENSE file in the project's top-level directory for details.

   Authors:
     * Martin Wittemann (martinwittemann)
     * Sebastian Werner (wpbasti)
     * Jonathan Rass (jonathan_rass)

************************************************************************ */
/**
 * @appearance combobox
 */
qx.Class.define("qx.ui.form.ComboBox",
{
  extend  : qx.ui.form.AbstractSelectBox,

  /*
  *****************************************************************************
     CONSTRUCTOR
  *****************************************************************************
  */

  construct : function()
  {
    this.base(arguments);

    this._createChildControl("textfield");
    this._createChildControl("button");
  },



  /*
  *****************************************************************************
     PROPERTIES
  *****************************************************************************
  */

  properties :
  {
    // overridden
    focusable :
    {
      refine : true,
      init : true
    },

    // overridden
    appearance :
    {
      refine : true,
      init : "combobox"
    }
  },



  /*
  *****************************************************************************
     MEMBERS
  *****************************************************************************
  */

  members :
  {
    /*
    ---------------------------------------------------------------------------
      WIDGET API
    ---------------------------------------------------------------------------
    */

    // overridden
    _createChildControlImpl : function(id)
    {
      var control;

      switch(id)
      {
        case "textfield":
          control = new qx.ui.form.TextField();
          control.setFocusable(false);
          this._add(control, {flex: 1});
          break;

        case "button":
          control = new qx.ui.form.Button();
          control.setFocusable(false);
          control.addListener("activate", this._onActivateButton, this);
          control.addListener("click", this._onClick, this);
          this._add(control);
          break;
      }

      return control || this.base(arguments, id);
    },


    // overridden
    _forwardStates : {
      focused : true
    },


    // overridden
    tabFocus : function() {
      this._getChildControl("textfield").getFocusElement().focus();
    },




    /*
    ---------------------------------------------------------------------------
      APPLY ROUTINES
    ---------------------------------------------------------------------------
    */

    // property apply
    _applySelected : function(value, old)
    {
      this.base(arguments, value, old);

      this._getChildControl("textfield").setValue(value.getLabel());
    },




    /*
    ---------------------------------------------------------------------------
      EVENT LISTENERS
    ---------------------------------------------------------------------------
    */

    /**
     * Toggles the popup's visibility.
     * @param e {qx.event.type.MouseEvent} Mouse click event
     * @type member
     */
    _onClick : function(e) {
      this._togglePopup();
    },


    /**
     * Redirect activation to the main widget
     * @param e {Object} Activation event
     * @type member
     */
    _onActivateButton : function(e)
    {
      this.activate();
      e.stopPropagation();
    }
  }
});
