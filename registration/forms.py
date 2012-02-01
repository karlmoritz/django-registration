"""
Forms and validation code for user registration.

"""

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django import forms
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class RegistrationForm(forms.Form):
    """
    Form for registering a new user account.
    
    Validates that the requested username is not already in use, and
    requires the password to be entered twice to catch typos.
    
    Subclasses should feel free to add any additional validation they
    need, but should avoid defining a ``save()`` method -- the actual
    saving of collected user data is delegated to the active
    registration backend.
    
    """
    username = forms.RegexField(regex=r'^\w+$',
                            max_length=30,
                            widget=forms.TextInput(),
                            label=_("Username"),
                            error_messages={'invalid': _("This value must contain only letters, numbers and underscores.")})
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(maxlength=75)),
                            label=_("Email address"))
    password1 = forms.CharField(widget=forms.PasswordInput(render_value=False),
                            label=_("Password"))
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False),
                            label=_("Reenter Password"))
    email.required = False
    
    def clean_username(self):
        """
        Validate that the username is alphanumeric and is not already
        in use.
        
        """
        try:
            user = User.objects.get(username__iexact=self.cleaned_data['username'])
        except User.DoesNotExist:
            return self.cleaned_data['username']
        raise forms.ValidationError(_("A user with that username already exists."))
    
    def clean(self):
        """
        Verifiy that the values entered into the two password fields
        match. Note that an error here will end up in
        ``non_field_errors()`` because it doesn't apply to a single
        field.
        
        """
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_("The two password fields didn't match."))
        return self.cleaned_data
        
    def clean_email(self):
        """
        Validate that the supplied email address is unique for the
        site.
        
        """
        if self.cleaned_data['email']:
          if User.objects.filter(email__iexact=self.cleaned_data['email']):
              raise forms.ValidationError(_("This email address is already in use. Please supply a different email address."))
          return self.cleaned_data['email']
        
        
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'id-exampleForm'
        self.helper.form_class = 'blueForms'
        self.helper.form_method = 'post'
        self.helper.form_action = 'registration_register'
        self.helper.add_input(Submit('submit', 'Submit'))
        super(RegistrationForm, self).__init__(*args, **kwargs)
        


class RegistrationFormTermsOfService(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which adds a required checkbox
    for agreeing to a site's Terms of Service.
    
    """
    tos = forms.BooleanField(widget=forms.CheckboxInput(),
                            label=_(u'I have read and agree to the Terms of Service'),
                            error_messages={'required': _("You must agree to the terms to register")})


class RegistrationFormUniqueEmail(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which enforces uniqueness of
    email addresses.
    
    """
    def clean_email(self):
        """
        Validate that the supplied email address is unique for the
        site.
        
        """
        if User.objects.filter(email__iexact=self.cleaned_data['email']):
            raise forms.ValidationError(_("This email address is already in use. Please supply a different email address."))
        return self.cleaned_data['email']


class RegistrationFormNoFreeEmail(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which disallows registration with
    email addresses from popular free webmail services; moderately
    useful for preventing automated spam registrations.
    
    To change the list of banned domains, subclass this form and
    override the attribute ``bad_domains``.
    
    """
    bad_domains = ['aim.com', 'aol.com', 'email.com', 'gmail.com',
                   'googlemail.com', 'hotmail.com', 'hushmail.com',
                   'msn.com', 'mail.ru', 'mailinator.com', 'live.com',
                   'yahoo.com']
    
    def clean_email(self):
        """
        Check the supplied email address against a list of known free
        webmail domains.
        
        """
        email_domain = self.cleaned_data['email'].split('@')[1]
        if email_domain in self.bad_domains:
            raise forms.ValidationError(_("Registration using free email addresses is prohibited. Please supply a different email address."))
        return self.cleaned_data['email']


class EmailRegistrationForm(forms.Form):
    """
    Form for registering a new user account.
    
    Validates that the requested username is not already in use, and
    requires the password to be entered twice to catch typos.
    
    Subclasses should feel free to add any additional validation they
    need, but should avoid defining a ``save()`` method -- the actual
    saving of collected user data is delegated to the active
    registration backend.
    
    """
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(maxlength=75)),
                             label=_("Email address"))
    password1 = forms.CharField(widget=forms.PasswordInput(render_value=False),
                                label=_("Password"))
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False),
                                label=_("Reenter Password"))
    
    def clean_email(self):
        """
        Validate that the supplied email address is unique for the
        site.
        
        """
        if User.objects.filter(email=self.cleaned_data['email'].lower()):
            raise forms.ValidationError(_("This email address is already in use. Please supply a different email address."))
        return self.cleaned_data['email'].lower()
    
    
    def clean(self):
        """
        Verifiy that the values entered into the two password fields
        match. Note that an error here will end up in
        ``non_field_errors()`` because it doesn't apply to a single
        field.
        
        """
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_("The two password fields didn't match."))
        return self.cleaned_data




################################################################################
# Authentication Forms

class EmailAuthenticationForm(forms.Form):
    """
    Replacement to do authentication with email 
    this is used in conjunction with auth.EmailModelBackend to accept email
    
    """
    email = forms.EmailField(label=_("Email"), max_length=255)
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput(render_value=False))
    
    def __init__(self, request=None, *args, **kwargs):
        """
        If request is passed in, the form will validate that cookies are
        enabled. Note that the request (a HttpRequest object) must have set a
        cookie with the key TEST_COOKIE_NAME and value TEST_COOKIE_VALUE before
        running this validation.
        """
        self.request = request
        self.user_cache = None
        super(EmailAuthenticationForm, self).__init__(*args, **kwargs)
    
    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        
        if email and password:
            self.user_cache = authenticate(email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_("Please enter a correct email and password. Note that both fields are case-sensitive."))
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("This account is inactive."))
        
        # TODO: determine whether this should move to its own method.
        if self.request:
            if not self.request.session.test_cookie_worked():
                raise forms.ValidationError(_("Your Web browser doesn't appear to have cookies enabled. Cookies are required for logging in."))
        
        return self.cleaned_data
    
    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None
    
    def get_user(self):
        return self.user_cache


class EmailOrCharField(forms.CharField):
    default_error_messages = {
        'invalid': _(u'Enter a valid e-mail address or username.'),
    }
    def clean(self, value):
        value = self.to_python(value).strip()
        return super(EmailOrCharField, self).clean(value)
    
    def validate(self, value):
        "Check that the value is only a username or an email."
        # Make sure that the CharField part is valid
        super(EmailOrCharField, self).validate(value)
        
        # If there is an '@', validate as an email address
        if '@' in value:
            from django.core.validators import validate_email
            validate_email(value)
        else:
            # It should be a username so make sure it is valid
            from django.core.validators import RegexValidator
            import re
            validator = RegexValidator(regex=re.compile(r'^\w+$'),
                message=u"This value must contain only letters, numbers and underscores.")
            validator(value)
    


class EmailOrUsernameAuthenticationForm(forms.Form):
    """
    Replacement to do authentication with an email or username
    this is used in conjunction with auth.EmailModelBackend to accept email
    
    """
    email = EmailOrCharField(label=_("Email or username"),
                        max_length=255,
                        widget=forms.TextInput(attrs={'placeholder': _('Email or username')}))
    password = forms.CharField(label=_("Password"),
                        widget=forms.PasswordInput(render_value=False, attrs={'placeholder': _('Password')}))
    persistent = forms.BooleanField(label=_("Keep me logged in"),
                        required=False,
                        initial=True)
    
    def __init__(self, request=None, *args, **kwargs):
        """
        If request is passed in, the form will validate that cookies are
        enabled. Note that the request (a HttpRequest object) must have set a
        cookie with the key TEST_COOKIE_NAME and value TEST_COOKIE_VALUE before
        running this validation.
        """
        self.request = request
        self.user_cache = None
        super(EmailOrUsernameAuthenticationForm, self).__init__(*args, **kwargs)
    
    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        persistent = self.cleaned_data.get('persistent')
        
        if email and password:
            if '@' in email:
                # We got an email address
                self.user_cache = authenticate(email=email, password=password)
            else:
                # Log in with a username
                self.user_cache = authenticate(username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_("Please enter a correct username or email and password. Note that both fields are case-sensitive."))
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("This account is inactive."))
        
        if self.request:
            if self.request.session and not persistent:
                # Mark the session cookie as going away when the window gets closed
                self.request.session.set_expiry(0)
        
        return self.cleaned_data
    
    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None
    
    def get_user(self):
        return self.user_cache

