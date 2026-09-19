from django import forms

from .models import Application, Candidate, JobPosting


class StyledModelForm(forms.ModelForm):
    """Same styling convention you use in employee_app.forms."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs.setdefault("class", "form-control")


class CommaListField(forms.CharField):
    """Accepts 'python, django, drf' and stores ['python','django','drf']."""
    def prepare_value(self, value):
        if isinstance(value, list):
            return ", ".join(value)
        return value

    def to_python(self, value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [part.strip() for part in value.split(",") if part.strip()]


class JobPostingForm(StyledModelForm):
    must_have_skills = CommaListField(required=False, help_text="Comma separated")
    good_to_have_skills = CommaListField(required=False, help_text="Comma separated")

    class Meta:
        model = JobPosting
        fields = (
            "title", "department", "designation", "description",
            "must_have_skills", "good_to_have_skills",
            "min_experience_years", "max_experience_years",
            "location", "openings", "status", "hiring_manager",
        )
        widgets = {"description": forms.Textarea(attrs={"rows": 8})}

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("min_experience_years"), cleaned.get("max_experience_years")
        if low is not None and high is not None and high < low:
            self.add_error("max_experience_years", "Maximum must be greater than minimum.")
        return cleaned


class CandidateForm(StyledModelForm):
    job = forms.ModelChoiceField(
        queryset=JobPosting.objects.filter(status=JobPosting.Status.OPEN),
        help_text="Application will be created for this job posting.",
    )
    run_agent_now = forms.BooleanField(
        required=False, initial=True, label="Screen with the AutoHire agent immediately",
    )

    class Meta:
        model = Candidate
        fields = ("full_name", "email", "mobile", "source", "resume_file")

    def clean_resume_file(self):
        resume = self.cleaned_data["resume_file"]
        if resume.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Resume must be under 5 MB.")
        if not resume.name.lower().endswith((".pdf", ".docx", ".txt")):
            raise forms.ValidationError("Upload a PDF, DOCX or TXT file.")
        return resume


class CheckpointDecisionForm(forms.Form):
    decision = forms.ChoiceField(
        choices=(("APPROVE", "Approve"), ("REJECT", "Decline")),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3,
                                     "placeholder": "Optional note for the audit trail"}),
    )


class ApplicationFilterForm(forms.Form):
    stage = forms.ChoiceField(
        required=False,
        choices=(("", "All stages"),) + tuple(Application.Stage.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    min_score = forms.IntegerField(
        required=False, min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Min score"}),
    )