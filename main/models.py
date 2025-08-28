from django.db import models
from django.contrib.auth.models import User
from django.forms import ValidationError
import pytz
from django.utils import timezone

class UserLeader(models.Model):
    user = models.OneToOneField(User, related_name='leader', on_delete=models.CASCADE)
    leader = models.ForeignKey(User, related_name='team_members', on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('user', 'leader')
    
    def __str__(self) -> str:
        return f"{self.user.username} --> {self.leader.username}"


class Lead(models.Model):
    name = models.CharField(max_length=255, unique=True, db_collation='utf8mb4_general_ci')
    # time_zone = models.CharField(max_length=30, blank=True, null=True)  # Moved to LeadPhoneNumbers

    def __str__(self) -> str:
        return f"{self.name}"   


# The excel Sheet that the Leads team upload (the first source of data that gets cut and distributed)

class Sheet(models.Model):
    name = models.CharField(max_length=250, db_collation='utf8mb4_general_ci')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_done = models.BooleanField(default=False)
    done_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    leads = models.ManyToManyField(Lead, related_name='sheets')
    is_approved = models.BooleanField(default=False)    #True when the team leader approves the upload process
    is_archived = models.BooleanField(default=False)
    is_x = models.BooleanField(default=False)           # true for x shows - bussiness needs - handled differently   
    
    def __str__(self):
        return self.name


class LeadPhoneNumbers(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    sheet = models.ForeignKey(Sheet, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)
    time_zone = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        unique_together = ('lead', 'sheet', 'value')


class LeadEmails(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    sheet = models.ForeignKey(Sheet, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)
    
    class Meta:
        unique_together = ('lead', 'sheet', 'value')


class LeadContactNames(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    sheet = models.ForeignKey(Sheet, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('lead', 'sheet', 'value')


class Acceptance(models.Model):
    ACCEPTANCE_TYPES = [
        (0, 'Decline'),
        (1, 'Accept'),
    ]
    sheet = models.ForeignKey(Sheet, on_delete=models.CASCADE)
    acceptance_type = models.IntegerField(choices=ACCEPTANCE_TYPES)
    team_leader = models.ForeignKey(User, on_delete=models.CASCADE)
    approved_at = models.DateTimeField(auto_now_add=True)


class TerminationCode(models.Model):
    name = models.CharField(max_length=10)
    full_name = models.CharField(max_length=25)

    def __str__(self):
        return self.name


class ReadyShow(models.Model):
    LABEL_CHOICES = [
        ('EHUB', 'EHUB'),
        ('EHUB2', 'EHUB2'),
        ('EP', 'EP'),
        ('UK', 'UK'),
        ('Europe', 'Europe'),
        ('Asia', 'Asia'),
    ]

    name = models.CharField(max_length=255)    # That is not used i use the name in the sheet because it is the same when cutting every cut show is not in the same page
    sheet = models.ForeignKey(Sheet, on_delete=models.SET_NULL, null=True)
    leads = models.ManyToManyField(Lead, related_name='ready_shows')
    is_done = models.BooleanField(default=False)       #To mark the show done after cutting it
    is_archived = models.BooleanField(default=False)
    done_date = models.DateTimeField(null=True, blank=True)
    label = models.CharField(max_length=10, choices=LABEL_CHOICES, default='EHUB')


class SalesShow(models.Model):
    LABEL_CHOICES = [
        ('EHUB', 'EHUB'),
        ('EHUB2', 'EHUB2'),
        ('EP', 'EP'),
        ('UK', 'UK'),
        ('Europe', 'Europe'),
        ('Asia', 'Asia'),
    ]

    Agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=255)
    sheet = models.ForeignKey(Sheet, on_delete=models.SET_NULL, null=True)
    leads = models.ManyToManyField(Lead, related_name='sales_shows')
    is_done = models.BooleanField(default=False)       #To mark the show done after finished
    done_date = models.DateTimeField(null=True, blank=True)
    is_recycled = models.BooleanField(default=False)   #To retreive the done show to be reycled
    rec_date = models.DateTimeField(null=True, blank=True)
    is_done_rec = models.BooleanField(default=False)   #To mark the show done after the recycle stage
    done_rec_date = models.DateTimeField(null=True, blank=True)
    label = models.CharField(max_length=10, choices=LABEL_CHOICES, default='EHUB')
    is_archived = models.BooleanField(default=False)       # To Archive the show 
    is_x = models.BooleanField(default=False)
    is_reassigned = models.BooleanField(default=False)
    is_done_reassigned = models.BooleanField(default=False)


    def __str__(self) -> str:
        return self.name


class PriceRequest(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    show = models.ForeignKey(SalesShow, on_delete=models.CASCADE)
    options = models.TextField()
    status = models.CharField(max_length=20, choices=[('booked', 'Booked'), ('not_booked', 'Not Booked')], null=True)
    num_rooms = models.PositiveIntegerField(null=True, blank=True)
    num_nights = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(null=True)
    email_status = models.CharField(max_length=20, choices=[('sent', 'Sent'), ('not_sent', 'Not Sent')], null=True)
    lead_status = models.CharField(max_length=20, choices=[('deal', 'Deal'), ('pending', 'Pending'), ('dead', 'Dead')], null=True)

    def __str__(self):
        return f"Price Request for {self.lead.name}"


class LeadTerminationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    flag = models.ForeignKey(TerminationCode, on_delete=models.CASCADE)   # The terminatin code value
    sales_show = models.ForeignKey(SalesShow, on_delete=models.CASCADE)
    CB_date = models.DateTimeField(null=True)
    notes = models.TextField(null=True)
    is_qualified = models.BooleanField(default=False)
    entry_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('booked', 'Booked'), ('not_booked', 'Not Booked')], null=True)
    num_rooms = models.PositiveIntegerField(null=True, blank=True)
    num_nights = models.PositiveIntegerField(null=True, blank=True)
    options = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ('lead', 'sales_show', 'flag')


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Move to PriceRequest if options field is not empty
        if type(self.options)==str and str(self.options).strip() != '':
            PriceRequest.objects.get_or_create(lead=self.lead, show=self.sales_show, options=self.options, num_nights=self.num_nights, num_rooms=self.num_rooms, notes=self.notes, status=self.status)


# Shows from the sales inventory that couldn't be linked to the sheets
class OldShow(models.Model):
    name = models.CharField(max_length=255)


class LeadTerminationHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    entry_date = models.DateTimeField(auto_now_add=True)
    termination_code = models.ForeignKey(TerminationCode, on_delete=models.CASCADE)
    cb_date = models.DateTimeField(null=True)
    notes = models.TextField(null=True)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    show = models.ForeignKey(SalesShow, null=True, blank=True, on_delete=models.CASCADE)
    old_show = models.ForeignKey(OldShow, null=True, blank=True, on_delete=models.CASCADE)

    def clean(self):
        # Ensure only one of sales_show or old_show is set
        if self.sales_show and self.old_show:
            raise ValidationError("You cannot set both SalesShow and OldShow.")
        if not self.sales_show and not self.old_show:
            raise ValidationError("You must set either SalesShow or OldShow.")

    def __str__(self):
        return f"LeadTerminationHistory: {self.lead} - {self.termination_code}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        (0, 'Import Request'),
        (1, 'Acceptance Notification'),
        (2, 'Decline Notification'),
        (3, 'Autofill Request'),
        (4, 'Autofill Request accepted'),
        (5, 'Close Call back Date'),
        (6, 'Referral'),
    ]
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_notifications')
    message = models.CharField(max_length=500)
    notification_type = models.IntegerField(choices=NOTIFICATION_TYPES)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)
    sheets = models.ManyToManyField(Sheet, blank=True)


class Log(models.Model):
    message = models.CharField(max_length=255)
    date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        from IBH.settings import TIME_ZONE 
        cairo_tz = pytz.timezone(TIME_ZONE)
        self.date = timezone.localtime(timezone.now(), cairo_tz)
        super().save(*args, **kwargs)


class LatestSheet(models.Model):
    main_sheet = models.ForeignKey(Sheet, on_delete=models.CASCADE, related_name="main_sheet")
    latest_sheet = models.ForeignKey(Sheet, on_delete=models.CASCADE, related_name="latest_sheet")
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class LeadsAverage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sheet = models.ForeignKey(Sheet, on_delete=models.CASCADE)
    count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class SalesTeams(models.Model): 
    LABEL_CHOICES = [
        ('EHUB', 'EHUB'),
        ('EHUB2', 'EHUB2'),
        ('EP', 'EP'),
        ('UK', 'UK'),
    ]

    label = models.CharField(max_length=10, choices=LABEL_CHOICES, default='EHUB')
    leader = models.ForeignKey(User, on_delete=models.CASCADE)
    openers_closers = models.ManyToManyField(User, related_name='openers_closers', blank=True)  # Team leaders previleges


class FilterType(models.Model):
    EMAIL = 'email'
    PHONE_NUMBER = 'phone_number'

    FILTER_TYPE_CHOICES = [
        (EMAIL, 'Email'),
        (PHONE_NUMBER, 'Phone Number'),
    ]

    name = models.CharField(max_length=20, choices=FILTER_TYPE_CHOICES, unique=True)

    def __str__(self):
        return self.get_name_display()


class FilterWords(models.Model):
    filter_types = models.ManyToManyField(FilterType, related_name='words')  # Many-to-Many to allow multiple filter types
    word = models.CharField(max_length=255)  # The word to be filtered

    def __str__(self):
        filter_types = ', '.join([ft.get_name_display() for ft in self.filter_types.all()])
        return f"{self.word} ({filter_types})"


class Referral(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    sheet = models.ForeignKey(Sheet, on_delete=models.SET_NULL, null=True)
    entry_date = models.DateTimeField(auto_now_add=True)


class LeadsColors(models.Model):
    COLOR_CHOICES = [
        ('white', 'White'),
        ('green', 'Green'),
        ('blue', 'Blue'),
        ('red', 'Red'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    sheet = models.ForeignKey(Sheet, on_delete=models.SET_NULL, null=True)
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default='white')

    def __str__(self):
        return f"{self.lead.name} - {self.get_color_display()}"


class SalesLog(models.Model):
    message = models.CharField(max_length=255)
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class IncomingsCount(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class TaskLog(models.Model):
    task_name = models.CharField(max_length=255, unique=True)
    last_run = models.DateTimeField()

    def __str__(self):
        return self.task_name



