// Global JavaScript functions for StockTrack

// Add animation to dashboard cards
document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('show');
        }, index * 100);
    });
});

// Format currency fields
function formatCurrency(input) {
    let value = input.value.replace(/[^\d.]/g, '');
    if (value) {
        value = parseFloat(value).toFixed(2);
        input.value = value;
    }
}

// Validate stock quantity
function validateQuantity(input) {
    let value = input.value.replace(/[^\d]/g, '');
    input.value = value;
}

// Confirm delete
function confirmDelete(event, itemName) {
    if (!confirm(`Are you sure you want to delete "${itemName}"? This action cannot be undone.`)) {
        event.preventDefault();
    }
}