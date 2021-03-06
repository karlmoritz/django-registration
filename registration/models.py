import datetime
import random
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db import transaction
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.utils.hashcompat import sha_constructor
from django.utils.translation import ugettext_lazy as _

SHA1_RE = re.compile('^[a-f0-9]{40}$')

class RegistrationManager(models.Manager):
    """
    Custom manager for the ``RegistrationProfile`` model.
    
    The methods defined here provide shortcuts for account creation
    and activation (including generation and emailing of activation
    keys), and for cleaning out expired inactive accounts.
    
    """
    def activate_user(self, activation_key):
        """
        Validate an activation key and activate the corresponding
        ``User`` if valid.
        
        If the key is valid and has not expired, return the ``User``
        after activating.
        
        If the key is not valid or has expired, return ``False``.
        
        If the key is valid but the ``User`` is already active,
        return ``False``.
        
        To prevent reactivation of an account which has been
        deactivated by site administrators, the activation key is
        reset to the string constant ``RegistrationProfile.ACTIVATED``
        after successful activation.
        
        """
        # Make sure the key we're trying conforms to the pattern of a
        # SHA1 hash; if it doesn't, no point trying to look it up in
        # the database.
        if SHA1_RE.search(activation_key):
            try:
                profile = self.get(activation_key=activation_key)
            except self.model.DoesNotExist:
                return False
            if not profile.activation_key_expired():
                user = profile.user
                user.is_active = True
                user.save()
                profile.activated = True
                profile.save()
                return user
        return False
    
    def create_inactive_user(self, username, email, password,
                             site, send_email=True,
                             first_name=None, last_name=None,
                             is_active=False):
        """
        Create a new, inactive ``User``, generate a
        ``RegistrationProfile`` and email its activation key to the
        ``User``, returning the new ``User``.
        
        By default, an activation email will be sent to the new
        user. To disable this, pass ``send_email=False``.
        
        """
        new_user = User.objects.create_user(username, email, password)
        new_user.is_active = is_active
        if first_name and last_name:
            new_user.first_name = first_name
            new_user.last_name = last_name
        new_user.save()
        
        registration_profile = self.create_profile(new_user)
        
        if send_email:
            registration_profile.send_activation_email(site)
        
        return new_user
    create_inactive_user = transaction.commit_on_success(create_inactive_user)
    
    def create_profile(self, user):
        """
        Create a ``RegistrationProfile`` for a given
        ``User``, and return the ``RegistrationProfile``.
        
        The activation key for the ``RegistrationProfile`` will be a
        SHA1 hash, generated from a combination of the ``User``'s
        username and a random salt.
        
        """
        salt = sha_constructor(str(random.random())).hexdigest()[:5]
        username = user.username
        if isinstance(username, unicode):
            username = username.encode('utf-8')
        activation_key = sha_constructor(salt+username).hexdigest()
        return self.create(user=user, activation_key=activation_key)
        
    def delete_expired_users(self):
        raise DeprecationWarning("This method has been removed. Please use the 'delete_expired_users' on the correct backend.")
    

class RegistrationProfile(models.Model):
    """
    A simple profile which stores an activation key for use during
    user account registration.
    
    Generally, you will not want to interact directly with instances
    of this model; the provided manager includes methods
    for creating and activating new accounts, as well as for cleaning
    out accounts which have never been activated.
    
    While it is possible to use this model as the value of the
    ``AUTH_PROFILE_MODULE`` setting, it's not recommended that you do
    so. This model's sole purpose is to store data temporarily during
    account registration and activation.
    
    """
    
    user = models.OneToOneField(User, primary_key=True, verbose_name=_('User'))
    activated = models.BooleanField(default=False)
    activation_key = models.CharField(_('activation key'), max_length=40)
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date Created'))
    
    objects = RegistrationManager()
    
    class Meta:
        verbose_name = _('registration profile')
        verbose_name_plural = _('registration profiles')
    
    def __unicode__(self):
        return u"Registration information for %s" % self.user
    
    def is_activated(self):
        return self.activated
    
    def activation_key_expired(self):
        """
        Determine whether this ``RegistrationProfile``'s activation
        key has expired, returning a boolean -- ``True`` if the key
        has expired.
        
        Key expiration is determined by a two-step process:
        
        1. If the user has already activated, the key will have been
           reset to the string constant ``ACTIVATED``. Re-activating
           is not permitted, and so this method returns ``True`` in
           this case.
        
        2. Otherwise, the date the user signed up is incremented by
           the number of days specified in the setting
           ``ACCOUNT_ACTIVATION_DAYS`` (which should be the number of
           days after signup during which a user is allowed to
           activate their account); if the result is less than or
           equal to the current date, the key has expired and this
           method returns ``True``.
        
        """
        expiration_date = datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        return self.is_activated() or \
               (self.created + expiration_date <= datetime.datetime.now())
    activation_key_expired.boolean = True
    
    def send_activation_email(self, site):
        """
        Send an activation email to the user associated with this
        ``RegistrationProfile``.
        
        The activation email will make use of two templates:
        
        ``registration/activation_email_subject.txt``
            This template will be used for the subject line of the
            email. Because it is used as the subject line of an email,
            this template's output **must** be only a single line of
            text; output longer than one line will be forcibly joined
            into only a single line.
        
        ``registration/activation_email.txt``
            This template will be used for the body of the email.
        
        These templates will each receive the following context
        variables:
        
        ``activation_key``
            The activation key for the new account.
        
        ``expiration_days``
            The number of days remaining during which the account may
            be activated.
        
        ``site``
            An object representing the site on which the user
            registered; depending on whether ``django.contrib.sites``
            is installed, this may be an instance of either
            ``django.contrib.sites.models.Site`` (if the sites
            application is installed) or
            ``django.contrib.sites.models.RequestSite`` (if
            not). Consult the documentation for the Django sites
            framework for details regarding these objects' interfaces.
        
        """
        ctx_dict = {'activation_key': self.activation_key,
                    'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                    'site': site,
                    'user': self.user,
                    }
        subject = render_to_string('registration/activation_email_subject.txt',
                                   ctx_dict)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        
        text_content = render_to_string('registration/activation_email.txt',
                                   ctx_dict)
        try:
            html_content = render_to_string('registration/activation_email.html',
                                    ctx_dict)
        except TemplateDoesNotExist:
            html_content = None
        
        from django.core.mail import EmailMultiAlternatives
        msg = EmailMultiAlternatives(subject, text_content,
            settings.DEFAULT_FROM_EMAIL, [self.user.email])
        if html_content:
            msg.attach_alternative(html_content, "text/html")
        
        msg.send()
    
