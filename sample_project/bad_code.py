# Sample file with technical debt for demonstration

def process_user_data(name, email, age, address, phone, company, title, salary, benefits, start_date, department, manager, emergency_contact, notes, preferences, tags):
    """Function with too many parameters - code smell example"""
    
    if name:
        if email:
            if age > 18:
                if address:
                    if phone:
                        if company:
                            if title:
                                if salary > 0:
                                    if benefits:
                                        if start_date:
                                            # Deep nesting - another code smell
                                            print("Processing user...")
                                            # TODO: This is a hack, needs proper implementation
                                            return True
    return False

class DataProcessor:
    def __init__(self):
        pass
    
    def process_data(self):
        # FIXME: This method is doing too many things
        data = self.fetch_data()
        cleaned_data = self.clean_data(data)
        validated_data = self.validate_data(cleaned_data)
        transformed_data = self.transform_data(validated_data)
        saved_data = self.save_data(transformed_data)
        self.send_notification(saved_data)
        self.update_cache(saved_data)
        self.log_metrics(saved_data)
        # ... 50+ more lines of mixed responsibilities
        return saved_data
