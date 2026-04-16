import datetime
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Transaction, Category, Budget, COLOR_CHOICES


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'inputmode': 'email'}),
    )

    class Meta:
        model = User
        fields = ['email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже зарегистрирован.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email'].lower()
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'inputmode': 'email'}),
    )

    def clean_username(self):
        return self.cleaned_data['username'].lower()


class TransactionForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=datetime.date.today,
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={'inputmode': 'decimal', 'step': '0.01', 'min': '0.01'}
        ),
    )
    recurring_interval = forms.ChoiceField(
        choices=[('monthly', 'Ежемесячно'), ('weekly', 'Еженедельно')],
        required=False,
        label='Интервал',
    )

    class Meta:
        model = Transaction
        fields = ['transaction_type', 'amount', 'category', 'date', 'note', 'is_recurring']
        widgets = {
            'note': forms.TextInput(attrs={'placeholder': 'Заметка (необязательно)'}),
        }
        labels = {
            'transaction_type': 'Тип',
            'amount': 'Сумма',
            'category': 'Категория',
            'date': 'Дата',
            'note': 'Заметка',
            'is_recurring': 'Повторяющийся платёж',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(user__isnull=True),
                is_hidden=False,
            ).order_by('order', 'name')
        self.fields['category'].empty_label = 'Выберите категорию'
        # Set default date to today
        if not self.instance.pk:
            self.initial.setdefault('date', datetime.date.today())

    def clean(self):
        cleaned_data = super().clean()
        is_recurring = cleaned_data.get('is_recurring')
        interval = cleaned_data.get('recurring_interval')
        if is_recurring and not interval:
            self.add_error('recurring_interval', 'Выберите интервал повторения.')
        return cleaned_data


class CategoryForm(forms.ModelForm):
    color = forms.ChoiceField(
        choices=COLOR_CHOICES,
        widget=forms.RadioSelect(),
        label='Цвет',
    )

    class Meta:
        model = Category
        fields = ['name', 'icon', 'color', 'transaction_type']
        widgets = {
            'icon': forms.TextInput(attrs={'placeholder': '📦', 'maxlength': '10'}),
        }
        labels = {
            'name': 'Название',
            'icon': 'Иконка (эмодзи)',
            'transaction_type': 'Тип операций',
        }


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['limit_amount']
        widgets = {
            'limit_amount': forms.NumberInput(
                attrs={
                    'inputmode': 'decimal',
                    'step': '100',
                    'min': '0',
                    'placeholder': '30 000',
                }
            ),
        }
        labels = {
            'limit_amount': 'Лимит расходов на месяц, ₽',
        }
