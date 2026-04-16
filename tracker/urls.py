from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('password-reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('auth/telegram/', views.TelegramLoginView.as_view(), name='telegram_login'),

    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Transactions
    path('transactions/', views.TransactionListView.as_view(), name='transactions'),
    path('transactions/add/', views.TransactionCreateView.as_view(), name='transaction_add'),
    path('transactions/<int:pk>/edit/', views.TransactionUpdateView.as_view(), name='transaction_edit'),
    path('transactions/<int:pk>/delete/', views.TransactionDeleteView.as_view(), name='transaction_delete'),
    path('transactions/export/', views.ExportCSVView.as_view(), name='export_csv'),

    # Categories
    path('categories/', views.CategoryListView.as_view(), name='categories'),
    path('categories/add/', views.CategoryCreateView.as_view(), name='category_add'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),

    # Budget
    path('budget/', views.BudgetView.as_view(), name='budget'),

    # Stats
    path('stats/', views.StatsView.as_view(), name='stats'),

    # Recurring
    path('recurring/', views.RecurringListView.as_view(), name='recurring'),
    path('recurring/<int:pk>/toggle/', views.RecurringToggleView.as_view(), name='recurring_toggle'),
]
