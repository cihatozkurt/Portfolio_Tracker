from app.database.models import User, TaxClass

class TaxService:
    # Germany tax constants
    SPARERPAUSCHBETRAG_SINGLE = 1000  # €1,000 for singles
    SPARERPAUSCHBETRAG_MARRIED = 2000  # €2,000 for married couples
    ABGELTUNGSTEUER = 0.25  # 25% capital gains tax
    SOLIDARITAETSZUSCHLAG = 0.055  # 5.5% solidarity surcharge
    
    def __init__(self, user: User):
        self.user = user
    
    def get_sparerpauschbetrag(self):
        """Get tax-free allowance based on marital status"""
        if self.user.is_married:
            return self.SPARERPAUSCHBETRAG_MARRIED
        return self.SPARERPAUSCHBETRAG_SINGLE
    
    def get_remaining_allowance(self):
        """Get remaining tax-free allowance for the year"""
        total_allowance = self.get_sparerpauschbetrag()
        used = self.user.used_allowance if self.user.used_allowance else 0
        return max(0, total_allowance - used)
    
    def calculate_base_tax_rate(self):
        """Calculate base tax rate (Abgeltungsteuer + Soli)"""
        base_rate = self.ABGELTUNGSTEUER
        soli = base_rate * self.SOLIDARITAETSZUSCHLAG
        return base_rate + soli
    
    def calculate_total_tax_rate(self):
        """Calculate total tax rate including church tax if applicable"""
        base_rate = self.ABGELTUNGSTEUER
        
        if self.user.has_church_tax:
            church_rate = self.user.church_tax_rate if self.user.church_tax_rate else 0.08
            church_tax = base_rate * church_rate
        else:
            church_tax = 0
        
        soli = base_rate * self.SOLIDARITAETSZUSCHLAG
        total_rate = base_rate + soli + church_tax
        return total_rate
    
    def calculate_tax_on_gains(self, realized_gains: float):
        """Calculate tax on realized capital gains"""
        if realized_gains <= 0:
            return {
                "realized_gains": realized_gains,
                "taxable_gains": 0,
                "tax_free_amount": 0,
                "total_tax": 0,
                "effective_rate": 0,
                "net_gains": realized_gains,
                "breakdown": {
                    "abgeltungsteuer": 0,
                    "solidaritaetszuschlag": 0,
                    "kirchensteuer": 0
                }
            }
        
        remaining_allowance = self.get_remaining_allowance()
        tax_free_amount = min(realized_gains, remaining_allowance)
        taxable_gains = max(0, realized_gains - remaining_allowance)
        
        base_tax = taxable_gains * self.ABGELTUNGSTEUER
        soli_tax = base_tax * self.SOLIDARITAETSZUSCHLAG
        
        if self.user.has_church_tax:
            church_rate = self.user.church_tax_rate if self.user.church_tax_rate else 0.08
            church_tax = base_tax * church_rate
        else:
            church_tax = 0
        
        total_tax = base_tax + soli_tax + church_tax
        effective_rate = (total_tax / realized_gains * 100) if realized_gains > 0 else 0
        
        return {
            "realized_gains": realized_gains,
            "tax_free_amount": tax_free_amount,
            "taxable_gains": taxable_gains,
            "breakdown": {
                "abgeltungsteuer": base_tax,
                "solidaritaetszuschlag": soli_tax,
                "kirchensteuer": church_tax
            },
            "total_tax": total_tax,
            "effective_rate": effective_rate,
            "net_gains": realized_gains - total_tax
        }
    
    def estimate_selling_tax(self, symbol: str, quantity: float, 
                              current_price: float, avg_cost: float):
        """Estimate tax if selling a position"""
        proceeds = quantity * current_price
        cost_basis = quantity * avg_cost
        gain = proceeds - cost_basis
        
        tax_result = self.calculate_tax_on_gains(gain)
        
        return {
            "symbol": symbol,
            "quantity": quantity,
            "proceeds": proceeds,
            "cost_basis": cost_basis,
            "gain_loss": gain,
            "tax_free_amount": tax_result["tax_free_amount"],
            "taxable_gains": tax_result["taxable_gains"],
            "breakdown": tax_result["breakdown"],
            "total_tax": tax_result["total_tax"],
            "effective_rate": tax_result["effective_rate"],
            "net_gains": tax_result["net_gains"]
        }
    
    def get_tax_summary(self):
        """Get summary of user's tax situation"""
        tax_class_value = self.user.tax_class.value if self.user.tax_class else "1"
        church_rate = self.user.church_tax_rate if self.user.church_tax_rate else 0.08
        
        return {
            "country": self.user.country if self.user.country else "Germany",
            "tax_class": tax_class_value,
            "is_married": self.user.is_married if self.user.is_married else False,
            "annual_income": self.user.annual_income if self.user.annual_income else 0,
            "sparerpauschbetrag": self.get_sparerpauschbetrag(),
            "used_allowance": self.user.used_allowance if self.user.used_allowance else 0,
            "remaining_allowance": self.get_remaining_allowance(),
            "has_church_tax": self.user.has_church_tax if self.user.has_church_tax else False,
            "church_tax_rate": church_rate * 100 if self.user.has_church_tax else 0,
            "total_tax_rate": self.calculate_total_tax_rate() * 100
        }