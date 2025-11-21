"""
Unit tests for 10-Category Email Classification System.

Tests the new 10-category system with primary/secondary classification.
"""

import pytest
from agent_platform.classification.agents.rule_agent_10cat import classify_with_10_categories
from agent_platform.classification.models import EmailCategory


class TestRuleClassifier10Categories:
    """Test rule-based classification with 10 categories."""

    def test_wichtig_todo_classification(self):
        """Test classification of important action items."""
        result = classify_with_10_categories(
            email_id='test_1',
            subject='Bitte um Rückmeldung bis Freitag',
            body='Können Sie mir die Zahlen bis Freitag schicken?',
            sender='boss@company.com'
        )

        assert result['primary_category'] == 'wichtig_todo'
        assert result['primary_confidence'] > 0.7
        assert 'importance_score' in result
        assert result['importance_score'] >= 0.85

    def test_termine_classification(self):
        """Test classification of appointments and events."""
        result = classify_with_10_categories(
            email_id='test_2',
            subject='Meeting morgen um 14 Uhr',
            body='Können wir uns morgen treffen?',
            sender='colleague@company.com'
        )

        assert result['primary_category'] == 'termine'
        assert result['importance_score'] >= 0.80

    def test_finanzen_classification(self):
        """Test classification of finance and invoices."""
        result = classify_with_10_categories(
            email_id='test_3',
            subject='Rechnung #12345',
            body='Anbei finden Sie die Rechnung für November.',
            sender='billing@vendor.com'
        )

        assert result['primary_category'] == 'finanzen'
        assert result['importance_score'] >= 0.75

    def test_bestellungen_classification(self):
        """Test classification of orders and shipping."""
        result = classify_with_10_categories(
            email_id='test_4',
            subject='Ihre Bestellung wurde versandt',
            body='Tracking-Nummer: ABC123',
            sender='orders@amazon.com'
        )

        assert result['primary_category'] == 'bestellungen'
        assert result['importance_score'] >= 0.60

    def test_job_projekte_classification(self):
        """Test classification of work projects."""
        result = classify_with_10_categories(
            email_id='test_5',
            subject='Projekt Update Q4',
            body='Hier ist der Status zum Kundenprojekt.',
            sender='pm@company.com'
        )

        assert result['primary_category'] == 'job_projekte'
        assert result['importance_score'] >= 0.70

    def test_vertraege_classification(self):
        """Test classification of contracts and official documents."""
        result = classify_with_10_categories(
            email_id='test_6',
            subject='Vertrag zur Unterschrift',
            body='Bitte unterschreiben Sie den beigefügten Vertrag.',
            sender='legal@company.com'
        )

        assert result['primary_category'] == 'vertraege'
        assert result['importance_score'] >= 0.85

    def test_persoenlich_classification(self):
        """Test classification of personal communication."""
        result = classify_with_10_categories(
            email_id='test_7',
            subject='Grüße aus dem Urlaub',
            body='Hi, wie geht es dir?',
            sender='friend@gmail.com'
        )

        assert result['primary_category'] == 'persoenlich'
        assert result['importance_score'] >= 0.60

    def test_newsletter_classification(self):
        """Test classification of newsletters."""
        result = classify_with_10_categories(
            email_id='test_8',
            subject='Unser monatlicher Newsletter',
            body='Hier sind die neuesten Updates...',
            sender='newsletter@techcrunch.com'
        )

        assert result['primary_category'] == 'newsletter'
        assert result['importance_score'] <= 0.50

    def test_werbung_classification(self):
        """Test classification of marketing and promotions."""
        result = classify_with_10_categories(
            email_id='test_9',
            subject='50% RABATT nur heute!',
            body='Sichern Sie sich jetzt unsere Angebote!',
            sender='sale@zalando.de'
        )

        assert result['primary_category'] == 'werbung'
        assert result['importance_score'] <= 0.30

    def test_spam_classification(self):
        """Test classification of spam."""
        result = classify_with_10_categories(
            email_id='test_10',
            subject='Sie haben 1.000.000€ gewonnen!!!',
            body='Klicken Sie hier um Ihr Geld abzuholen',
            sender='scam@suspicious.ru'
        )

        assert result['primary_category'] == 'spam'
        assert result['importance_score'] <= 0.10

    def test_secondary_categories(self):
        """Test that secondary categories are assigned."""
        result = classify_with_10_categories(
            email_id='test_11',
            subject='Meeting zur Rechnung nächste Woche',
            body='Können wir nächsten Montag die Rechnung besprechen?',
            sender='boss@company.com'
        )

        # Should have primary + secondary categories
        assert result['primary_category'] in ['wichtig_todo', 'termine', 'finanzen']
        assert 'secondary_categories' in result
        assert isinstance(result['secondary_categories'], list)
        assert len(result['secondary_categories']) <= 3

    def test_confidence_scores(self):
        """Test that confidence scores are within valid range."""
        result = classify_with_10_categories(
            email_id='test_12',
            subject='Test email',
            body='This is a test.',
            sender='test@example.com'
        )

        assert 0.0 <= result['primary_confidence'] <= 1.0
        assert 0.0 <= result['importance_score'] <= 1.0

    def test_category_importance_mapping(self):
        """Test that all categories have defined importance scores."""
        from agent_platform.classification.models import CATEGORY_IMPORTANCE_MAP

        all_categories = [
            'wichtig_todo', 'termine', 'finanzen', 'bestellungen',
            'job_projekte', 'vertraege', 'persoenlich', 'newsletter',
            'werbung', 'spam'
        ]

        for category in all_categories:
            assert category in CATEGORY_IMPORTANCE_MAP
            importance = CATEGORY_IMPORTANCE_MAP[category]
            assert 0.0 <= importance <= 1.0


class TestPrimarySecondarySystem:
    """Test primary + secondary category assignment logic."""

    def test_max_three_secondary_categories(self):
        """Test that max 3 secondary categories are assigned."""
        # Complex email with multiple category signals
        result = classify_with_10_categories(
            email_id='test_13',
            subject='Meeting zu Vertrag, Rechnung und Projekt nächste Woche',
            body='Wir müssen mehrere Themen besprechen: den neuen Vertrag, '
                 'die offene Rechnung, und das aktuelle Projekt. Bitte Feedback bis Freitag.',
            sender='boss@company.com'
        )

        assert len(result['secondary_categories']) <= 3

    def test_no_duplicate_primary_in_secondary(self):
        """Test that primary category is not in secondary categories."""
        result = classify_with_10_categories(
            email_id='test_14',
            subject='Wichtige Aufgabe',
            body='Bitte erledigen Sie diese wichtige Aufgabe.',
            sender='boss@company.com'
        )

        assert result['primary_category'] not in result['secondary_categories']

    def test_empty_secondary_categories_possible(self):
        """Test that emails can have zero secondary categories."""
        result = classify_with_10_categories(
            email_id='test_15',
            subject='Test',
            body='Simple test email',
            sender='test@example.com'
        )

        # Secondary categories can be empty list
        assert isinstance(result['secondary_categories'], list)
