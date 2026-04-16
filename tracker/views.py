import csv
import datetime
import hashlib
import hmac
import secrets
import time
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordResetView as DjangoPasswordResetView
from django.db.models import Q, Sum
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, ListView, TemplateView, UpdateView,
)

from .forms import (
    BudgetForm, CategoryForm, LoginForm, RegisterForm, TransactionForm,
)
from .models import Budget, Category, RecurringRule, TelegramLoginToken, TelegramProfile, Transaction, SYSTEM_CATEGORIES


# ──────────────────────────────── helpers ────────────────────────────────────

def _current_month_range():
    today = datetime.date.today()
    return today.replace(day=1), today


def _get_budget(user, year, month):
    return Budget.objects.filter(user=user, year=year, month=month).first()


def _month_expenses(user, year, month):
    start = datetime.date(year, month, 1)
    if month == 12:
        end = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
    qs = Transaction.objects.filter(
        user=user, transaction_type='expense', date__range=(start, end)
    )
    total = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    return total, qs


# ──────────────────────────────── auth ───────────────────────────────────────

class RegisterView(View):
    template_name = 'tracker/auth/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name, {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Добро пожаловать! Аккаунт создан.')
            return redirect('dashboard')
        return render(request, self.template_name, {'form': form})


class LoginView(View):
    template_name = 'tracker/auth/login.html'

    def _context(self, form):
        return {
            'form': form,
            'telegram_bot_name': getattr(settings, 'TELEGRAM_BOT_NAME', ''),
        }

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name, self._context(LoginForm()))

    def post(self, request):
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(request.GET.get('next', 'dashboard'))
        return render(request, self.template_name, self._context(form))


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('login')


class PasswordResetView(DjangoPasswordResetView):
    template_name = 'tracker/auth/password_reset.html'
    email_template_name = 'tracker/auth/password_reset_email.txt'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        messages.info(self.request, 'Письмо с инструкцией отправлено на указанный email.')
        return super().form_valid(form)


def _check_telegram_auth(data: dict, bot_token: str) -> bool:
    """Validate Telegram Login Widget data using HMAC-SHA256."""
    check_hash = data.pop('hash')
    data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    auth_date_valid = (time.time() - int(data.get('auth_date', 0))) < 86400
    return hmac.compare_digest(computed_hash, check_hash) and auth_date_valid


class TelegramLoginView(View):
    """Handle Telegram Login Widget callback."""

    def get(self, request):
        params = request.GET.dict()
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')

        if not bot_token:
            messages.error(request, 'Telegram авторизация не настроена.')
            return redirect('login')

        if 'hash' not in params:
            messages.error(request, 'Некорректные данные авторизации Telegram.')
            return redirect('login')

        # _check_telegram_auth mutates the dict (pops 'hash'), so pass a copy
        params_copy = dict(params)
        try:
            valid = _check_telegram_auth(params_copy, bot_token)
        except Exception:
            valid = False

        if not valid:
            messages.error(request, 'Не удалось подтвердить авторизацию через Telegram.')
            return redirect('login')

        telegram_id = int(params['id'])
        username = params.get('username') or None
        first_name = params.get('first_name') or None
        last_name = params.get('last_name') or None
        photo_url = params.get('photo_url') or None

        # Find existing profile or create a new user
        profile = TelegramProfile.objects.filter(telegram_id=telegram_id).select_related('user').first()
        if profile:
            user = profile.user
        else:
            tg_username = f'tg_{telegram_id}'
            tg_email = f'tg_{telegram_id}@telegram.local'
            user, _ = User.objects.get_or_create(
                username=tg_username,
                defaults={'email': tg_email},
            )
            user.set_unusable_password()
            user.save(update_fields=['password'])
            profile = TelegramProfile(user=user, telegram_id=telegram_id)

        # Update profile fields
        profile.telegram_username = username
        profile.telegram_first_name = first_name
        profile.telegram_last_name = last_name
        profile.telegram_photo_url = photo_url
        profile.save()

        login(request, user)
        return redirect('/')


class TelegramAuthInitView(View):
    """Generate a one-time token and return the bot deep link."""

    def get(self, request):
        # Clean up expired tokens
        TelegramLoginToken.objects.filter(is_verified=False).exclude(
            created_at__gte=timezone.now() - datetime.timedelta(minutes=5)
        ).delete()

        token = TelegramLoginToken.objects.create(token=secrets.token_urlsafe(32))
        bot_name = getattr(settings, 'TELEGRAM_BOT_NAME', '')
        deep_link = f'https://t.me/{bot_name}?start=auth_{token.token}'
        return JsonResponse({'token': token.token, 'deep_link': deep_link})


class TelegramAuthPollView(View):
    """Poll whether the token has been verified by the bot."""

    def get(self, request):
        token_value = request.GET.get('token', '')
        if not token_value:
            return JsonResponse({'status': 'error'})

        try:
            token_obj = TelegramLoginToken.objects.get(token=token_value)
        except TelegramLoginToken.DoesNotExist:
            return JsonResponse({'status': 'error'})

        if token_obj.is_expired() and not token_obj.is_verified:
            token_obj.delete()
            return JsonResponse({'status': 'expired'})

        if token_obj.is_verified and token_obj.telegram_id:
            telegram_id = token_obj.telegram_id
            token_obj.delete()

            profile = TelegramProfile.objects.filter(telegram_id=telegram_id).select_related('user').first()
            if profile:
                user = profile.user
            else:
                tg_username = f'tg_{telegram_id}'
                tg_email = f'tg_{telegram_id}@telegram.local'
                user, _ = User.objects.get_or_create(
                    username=tg_username,
                    defaults={'email': tg_email},
                )
                user.set_unusable_password()
                user.save(update_fields=['password'])
                profile = TelegramProfile.objects.create(user=user, telegram_id=telegram_id)

            login(request, user)
            return JsonResponse({'status': 'ok'})

        return JsonResponse({'status': 'pending'})


# ──────────────────────────────── dashboard ──────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'tracker/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        today = datetime.date.today()
        year, month = today.year, today.month

        total_expense, _ = _month_expenses(user, year, month)
        total_income = Transaction.objects.filter(
            user=user, transaction_type='income',
            date__year=year, date__month=month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        budget = _get_budget(user, year, month)
        budget_pct = None
        budget_status = 'green'
        if budget and budget.limit_amount > 0:
            budget_pct = float(total_expense / budget.limit_amount * 100)
            if budget_pct >= 90:
                budget_status = 'red'
            elif budget_pct >= 70:
                budget_status = 'yellow'

        recent_transactions = Transaction.objects.filter(
            user=user
        ).select_related('category')[:10]

        ctx.update({
            'total_expense': total_expense,
            'total_income': total_income,
            'balance': total_income - total_expense,
            'budget': budget,
            'budget_pct': budget_pct,
            'budget_status': budget_status,
            'recent_transactions': recent_transactions,
            'today': today,
        })
        return ctx


# ──────────────────────────────── transactions ───────────────────────────────

class TransactionListView(LoginRequiredMixin, View):
    template_name = 'tracker/transactions/list.html'

    def get(self, request):
        user = request.user
        today = datetime.date.today()
        qs = Transaction.objects.filter(user=user).select_related('category')

        # Period filter
        period = request.GET.get('period', 'current')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')

        if period == 'current':
            start = today.replace(day=1)
            end = today
        elif period == 'last':
            first_this = today.replace(day=1)
            last_month_end = first_this - datetime.timedelta(days=1)
            start = last_month_end.replace(day=1)
            end = last_month_end
        elif period == 'custom' and date_from and date_to:
            try:
                start = datetime.date.fromisoformat(date_from)
                end = datetime.date.fromisoformat(date_to)
            except ValueError:
                start, end = today.replace(day=1), today
        else:
            start = today.replace(day=1)
            end = today

        qs = qs.filter(date__range=(start, end))

        # Type filter
        tx_type = request.GET.get('type', 'all')
        if tx_type == 'expense':
            qs = qs.filter(transaction_type='expense')
        elif tx_type == 'income':
            qs = qs.filter(transaction_type='income')

        # Category filter
        cat_ids = request.GET.getlist('categories')
        if cat_ids:
            qs = qs.filter(category_id__in=cat_ids)

        totals = qs.aggregate(
            expenses=Sum('amount', filter=Q(transaction_type='expense')),
            income=Sum('amount', filter=Q(transaction_type='income')),
        )
        total_expense = totals['expenses'] or Decimal('0')
        total_income = totals['income'] or Decimal('0')

        all_categories = Category.objects.filter(
            Q(user=user) | Q(user__isnull=True), is_hidden=False
        )

        return render(request, self.template_name, {
            'transactions': qs,
            'period': period,
            'date_from': start.isoformat(),
            'date_to': end.isoformat(),
            'tx_type': tx_type,
            'selected_cat_ids': [int(c) for c in cat_ids],
            'all_categories': all_categories,
            'total_expense': total_expense,
            'total_income': total_income,
            'balance': total_income - total_expense,
        })


class TransactionCreateView(LoginRequiredMixin, View):
    template_name = 'tracker/transactions/form.html'

    def _get_recent_categories(self, user):
        recent_ids = (
            Transaction.objects.filter(user=user)
            .order_by('-created_at')
            .values_list('category_id', flat=True)[:20]
        )
        seen, result = set(), []
        for cid in recent_ids:
            if cid not in seen:
                seen.add(cid)
                result.append(cid)
            if len(result) == 4:
                break
        return Category.objects.filter(id__in=result)

    def _ctx(self, form, recent_categories):
        return {
            'form': form,
            'title': 'Добавить транзакцию',
            'recent_categories': recent_categories,
            'today': datetime.date.today().isoformat(),
        }

    def get(self, request):
        form = TransactionForm(user=request.user)
        return render(request, self.template_name,
                      self._ctx(form, self._get_recent_categories(request.user)))

    def post(self, request):
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.user = request.user

            if tx.is_recurring:
                interval = form.cleaned_data['recurring_interval']
                rule = RecurringRule.objects.create(
                    user=request.user,
                    transaction_type=tx.transaction_type,
                    amount=tx.amount,
                    category=tx.category,
                    note=tx.note,
                    interval=interval,
                    day_of_month=tx.date.day if interval == 'monthly' else None,
                    day_of_week=tx.date.weekday() if interval == 'weekly' else None,
                    next_date=_next_recurring_date(tx.date, interval),
                )
                tx.recurring_rule = rule

            tx.save()
            messages.success(request, 'Транзакция добавлена.')
            return redirect('transactions')
        return render(request, self.template_name,
                      self._ctx(form, self._get_recent_categories(request.user)))


class TransactionUpdateView(LoginRequiredMixin, View):
    template_name = 'tracker/transactions/form.html'

    def _get_object(self, request, pk):
        return get_object_or_404(Transaction, pk=pk, user=request.user)

    def get(self, request, pk):
        tx = self._get_object(request, pk)
        initial = {}
        if tx.recurring_rule:
            initial['recurring_interval'] = tx.recurring_rule.interval
        form = TransactionForm(instance=tx, user=request.user, initial=initial)
        return render(request, self.template_name, {
            'form': form, 'title': 'Редактировать транзакцию', 'object': tx,
            'today': datetime.date.today().isoformat(),
        })

    def post(self, request, pk):
        tx = self._get_object(request, pk)
        form = TransactionForm(request.POST, instance=tx, user=request.user)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.save()
            messages.success(request, 'Транзакция обновлена.')
            return redirect('transactions')
        return render(request, self.template_name, {
            'form': form, 'title': 'Редактировать транзакцию', 'object': tx,
            'today': datetime.date.today().isoformat(),
        })


class TransactionDeleteView(LoginRequiredMixin, View):
    template_name = 'tracker/transactions/confirm_delete.html'

    def _get_object(self, request, pk):
        return get_object_or_404(Transaction, pk=pk, user=request.user)

    def get(self, request, pk):
        tx = self._get_object(request, pk)
        return render(request, self.template_name, {'object': tx})

    def post(self, request, pk):
        tx = self._get_object(request, pk)
        tx.delete()
        messages.success(request, 'Транзакция удалена.')
        return redirect('transactions')


class ExportCSVView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        today = datetime.date.today()

        period = request.GET.get('period', 'current')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')

        if period == 'current':
            start = today.replace(day=1)
            end = today
        elif period == 'last':
            first_this = today.replace(day=1)
            last_month_end = first_this - datetime.timedelta(days=1)
            start = last_month_end.replace(day=1)
            end = last_month_end
        elif period == 'custom' and date_from and date_to:
            try:
                start = datetime.date.fromisoformat(date_from)
                end = datetime.date.fromisoformat(date_to)
            except ValueError:
                start, end = today.replace(day=1), today
        else:
            start = today.replace(day=1)
            end = today

        qs = Transaction.objects.filter(
            user=user, date__range=(start, end)
        ).select_related('category').order_by('-date', '-created_at')

        filename = f'moneycheck_{start.strftime("%Y-%m")}.csv'
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['date', 'type', 'amount', 'category', 'note'])
        for tx in qs:
            writer.writerow([
                tx.date.isoformat(),
                tx.transaction_type,
                str(tx.amount),
                tx.category.name,
                tx.note,
            ])
        return response


# ──────────────────────────────── categories ─────────────────────────────────

class CategoryListView(LoginRequiredMixin, View):
    template_name = 'tracker/categories/list.html'

    def get(self, request):
        user = request.user
        user_categories = Category.objects.filter(user=user)
        system_categories = Category.objects.filter(user__isnull=True)
        return render(request, self.template_name, {
            'user_categories': user_categories,
            'system_categories': system_categories,
        })


class CategoryCreateView(LoginRequiredMixin, View):
    template_name = 'tracker/categories/form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': CategoryForm(), 'title': 'Новая категория',
        })

    def post(self, request):
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.user = request.user
            cat.order = Category.objects.filter(user=request.user).count() + 100
            cat.save()
            messages.success(request, 'Категория создана.')
            return redirect('categories')
        return render(request, self.template_name, {
            'form': form, 'title': 'Новая категория',
        })


class CategoryUpdateView(LoginRequiredMixin, View):
    template_name = 'tracker/categories/form.html'

    def _get_object(self, request, pk):
        return get_object_or_404(Category, pk=pk, user=request.user)

    def get(self, request, pk):
        cat = self._get_object(request, pk)
        return render(request, self.template_name, {
            'form': CategoryForm(instance=cat),
            'title': 'Редактировать категорию',
            'object': cat,
        })

    def post(self, request, pk):
        cat = self._get_object(request, pk)
        form = CategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, 'Категория обновлена.')
            return redirect('categories')
        return render(request, self.template_name, {
            'form': form,
            'title': 'Редактировать категорию',
            'object': cat,
        })


# ──────────────────────────────── budget ─────────────────────────────────────

class BudgetView(LoginRequiredMixin, View):
    template_name = 'tracker/budget.html'

    def _get_or_none(self, user):
        today = datetime.date.today()
        return Budget.objects.filter(
            user=user, year=today.year, month=today.month
        ).first()

    def get(self, request):
        budget = self._get_or_none(request.user)
        form = BudgetForm(instance=budget)
        return render(request, self.template_name, {'form': form, 'budget': budget})

    def post(self, request):
        budget = self._get_or_none(request.user)
        form = BudgetForm(request.POST, instance=budget)
        if form.is_valid():
            today = datetime.date.today()
            b = form.save(commit=False)
            b.user = request.user
            b.year = today.year
            b.month = today.month
            b.save()
            messages.success(request, 'Бюджет сохранён.')
            return redirect('dashboard')
        return render(request, self.template_name, {'form': form, 'budget': budget})


# ──────────────────────────────── stats ──────────────────────────────────────

class StatsView(LoginRequiredMixin, View):
    template_name = 'tracker/stats.html'

    def get(self, request):
        user = request.user
        today = datetime.date.today()

        period = request.GET.get('period', 'current')
        if period == 'last':
            first_this = today.replace(day=1)
            last_day = first_this - datetime.timedelta(days=1)
            year, month = last_day.year, last_day.month
        else:
            year, month = today.year, today.month

        start = datetime.date(year, month, 1)
        if month == 12:
            end = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

        expense_qs = Transaction.objects.filter(
            user=user, transaction_type='expense', date__range=(start, end)
        ).select_related('category')

        income_total = Transaction.objects.filter(
            user=user, transaction_type='income', date__range=(start, end)
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Group by category
        by_category = {}
        for tx in expense_qs:
            cat = tx.category
            if cat.id not in by_category:
                by_category[cat.id] = {
                    'category': cat, 'total': Decimal('0'), 'count': 0,
                }
            by_category[cat.id]['total'] += tx.amount
            by_category[cat.id]['count'] += 1

        sorted_cats = sorted(by_category.values(), key=lambda x: x['total'], reverse=True)
        total_expense = sum(c['total'] for c in sorted_cats)

        # Add percentage
        for item in sorted_cats:
            item['pct'] = float(item['total'] / total_expense * 100) if total_expense else 0

        budget = _get_budget(user, year, month)
        budget_pct = None
        budget_status = 'green'
        if budget and budget.limit_amount > 0:
            budget_pct = float(total_expense / budget.limit_amount * 100)
            if budget_pct >= 90:
                budget_status = 'red'
            elif budget_pct >= 70:
                budget_status = 'yellow'

        return render(request, self.template_name, {
            'period': period,
            'year': year,
            'month': month,
            'by_category': sorted_cats,
            'top3': sorted_cats[:3],
            'total_expense': total_expense,
            'total_income': income_total,
            'balance': income_total - total_expense,
            'budget': budget,
            'budget_pct': budget_pct,
            'budget_status': budget_status,
            'has_data': bool(sorted_cats),
        })


# ──────────────────────────────── recurring ──────────────────────────────────

class RecurringListView(LoginRequiredMixin, View):
    template_name = 'tracker/recurring/list.html'

    def get(self, request):
        rules = RecurringRule.objects.filter(
            user=request.user
        ).select_related('category')
        return render(request, self.template_name, {'rules': rules})


class RecurringToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        rule = get_object_or_404(RecurringRule, pk=pk, user=request.user)
        rule.is_active = not rule.is_active
        rule.save(update_fields=['is_active'])
        messages.success(
            request,
            f'Платёж {"включён" if rule.is_active else "отключён"}.',
        )
        return redirect('recurring')


# ──────────────────────────────── helpers ────────────────────────────────────

def _next_recurring_date(from_date, interval):
    if interval == 'monthly':
        month = from_date.month + 1
        year = from_date.year
        if month > 12:
            month = 1
            year += 1
        day = min(from_date.day, 28)
        return datetime.date(year, month, day)
    else:  # weekly
        return from_date + datetime.timedelta(weeks=1)
