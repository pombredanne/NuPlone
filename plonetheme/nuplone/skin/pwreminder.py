import logging
import socket
from Products.MailHost.MailHost import MailHostError
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName
from Acquisition import aq_inner
from five import grok
from zope import schema
from zope.i18n import translate
from plone.directives import form
from plonetheme.nuplone import MessageFactory as _
from z3c.form.button import buttonAndHandler
from Products.statusmessages.interfaces import IStatusMessage
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plonetheme.nuplone.utils import createEmailTo


log = logging.getLogger(__name__)


class IPasswordReset(form.Schema):
    login = schema.TextLine(
            title=_("label_login", default=u"Login"),
            required=True)


class PasswordReminderForm(form.SchemaForm):
    grok.context(ISiteRoot)
    grok.name("request-password-reset")
    grok.require("zope2.Public")

    email_template = ViewPageTemplateFile("templates/pwreset-email.pt")

    ignoreContext = True
    schema = IPasswordReset
    label = _(u"header_password_reset", default="Reset password")
    default_fieldset_label = None
    description = _(u"into_password_reset",
            default=u"For security reasons, we store your password encrypted, "
                    u"and cannot mail it to you. If you would like to reset "
                    u"your password, fill out the form below and we will send "
                    u"you an email at the address you gave when you registered "
                    u"to start the process of resetting your password.")


    @buttonAndHandler(_("button_send", default="Send"), name="send")
    def handleSend(self, action):
        flash=IStatusMessage(self.request).addStatusMessage
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        pas = getToolByName(self.context, "acl_users")
        mt = getToolByName(self.context, "portal_membership")
        user = pas.getUser(data["login"])
        if user is None:
            log.info("Password reset request for unknown user %s" % data["login"])
            flash(_("error_pwreset_unknown_user", default=u"Unknown username."), "error")
            return

        member = mt.getMemberById(user.getId())
        email_address = member.getProperty("email")
        if not email_address:
            flash(_("error_pwreset_no_email", default=u"No known email address for this user."), "error")
            return

        ppr = getToolByName(self.context, "portal_password_reset")
        reset = ppr.requestReset(user.getId())
        portal_url = aq_inner(self.context).absolute_url()
        reset_url = "%s/@@reset-password/%s" % (portal_url, reset["randomstring"])

        data["site"] = self.context.title
        subject=_(u"password_reset_subject", default=u"Password reset for ${site}", mapping=data)
        subject=translate(subject, context=self.request)
        body=self.email_template(reset_url=reset_url, login=data["login"], site=self.context.title)

        email=createEmailTo(self.context.email_from_name,
                            self.context.email_from_address,
                            None, email_address,
                            subject, body)

        mh=getToolByName(self.context, "MailHost")
        try:
            mh.send(email)
        except MailHostError, e:
            log.error("MailHost error sending password reset form to %s: %s", email_address, e)
            flash(_(u"error_contactmail", u"An error occured while processing your contact request. Please try again later."), "error")
            return
        except socket.error, e:
            log.error("Socket error sending password reset form to: %s", email_address, e[1])
            flash(_(u"error_contactmail", u"An error occured while processing your contact request. Please try again later."), "error")
            return

        flash(_("info_pwrest_mail_sent",
            default=u"An email with instructions for resetting your password has been sent."),
            "success")
        self.request.response.redirect(portal_url)



class PasswordReset(grok.View):
    grok.context(ISiteRoot)
    grok.name("reset-password")
    grok.require("zope2.Public")

    def render(self):
        return ""


