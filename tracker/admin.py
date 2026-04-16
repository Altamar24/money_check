from django.contrib import admin
from .models import Budget, Category, RecurringRule, TelegramProfile, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'user', 'transaction_type', 'is_hidden', 'order']
    list_filter = ['transaction_type', 'is_hidden']
    search_fields = ['name']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'transaction_type', 'amount', 'category', 'note']
    list_filter = ['transaction_type', 'date']
    search_fields = ['user__email', 'note']
    date_hierarchy = 'date'


@admin.register(RecurringRule)
class RecurringRuleAdmin(admin.ModelAdmin):
    list_display = ['user', 'interval', 'amount', 'category', 'next_date', 'is_active']
    list_filter = ['interval', 'is_active']
    search_fields = ['user__email']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['user', 'year', 'month', 'limit_amount']
    search_fields = ['user__email']


@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'telegram_id', 'telegram_username', 'created_at']
    search_fields = ['user__email', 'telegram_username', 'telegram_id']
