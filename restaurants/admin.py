from django.contrib import admin
from django.utils import timezone
from .models import Restaurant, RestaurantClaim, RestaurantTable, MenuItem, Review


@admin.action(description="Approve selected claims and activate Waqt LIVE status")
def approve_claims(modeladmin, request, queryset):
    count = 0
    for claim in queryset.filter(status='PENDING'):
        claim.status = 'VERIFIED'
        claim.reviewed_at = timezone.now()
        claim.save(update_fields=['status', 'reviewed_at'])

        # Update restaurant
        rest = claim.restaurant
        rest.owner = claim.claimant
        rest.claim_status = 'VERIFIED'
        rest.waqt_status = 'LIVE'
        rest.is_verified = True
        rest.save(update_fields=['owner', 'claim_status', 'waqt_status', 'is_verified'])

        # Upgrade claimant user role to OWNER
        user = claim.claimant
        if user.role != 'OWNER':
            user.role = 'OWNER'
            user.save(update_fields=['role'])

        count += 1
    modeladmin.message_user(request, f"{count} claim(s) approved. Restaurants assigned to owners and upgraded to LIVE.")


@admin.action(description="Reject selected claims and restore UNCLAIMED status")
def reject_claims(modeladmin, request, queryset):
    count = 0
    for claim in queryset.filter(status='PENDING'):
        claim.status = 'REJECTED'
        claim.reviewed_at = timezone.now()
        claim.save(update_fields=['status', 'reviewed_at'])

        rest = claim.restaurant
        if rest.claim_status == 'PENDING':
            rest.claim_status = 'UNCLAIMED'
            rest.save(update_fields=['claim_status'])
        count += 1
    modeladmin.message_user(request, f"{count} claim(s) rejected.")


@admin.register(RestaurantClaim)
class RestaurantClaimAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'claimant', 'full_name', 'phone', 'role_in_business', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('restaurant__name', 'claimant__username', 'full_name', 'phone')
    actions = [approve_claims, reject_claims]


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'locality', 'cuisine_type', 'waqt_status', 'claim_status', 'owner', 'is_active', 'is_verified')
    list_filter = ('waqt_status', 'claim_status', 'is_active', 'is_verified', 'locality')
    search_fields = ('name', 'locality', 'cuisine_type', 'address')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(RestaurantTable)
class RestaurantTableAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'table_number', 'capacity', 'status', 'created_at')
    list_filter = ('status', 'capacity')
    search_fields = ('restaurant__name', 'table_number')


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'category', 'price', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'restaurant__name')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'customer', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('restaurant__name', 'customer__username', 'comment')
