from flask import Flask, request, jsonify
from datetime import datetime
import logging
import os

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/webhook/task-completed', methods=['POST'])
def handle_task_completed():
    """
    Handle webhook when a task is marked as complete
    Expected payload: {
        "taskId": "string",
        "userId": "string",
        "projectId": "string",
        "taskType": "string",
        "estimatedHours": "number",
        "actualHours": "number",
        "completedAt": "ISO timestamp"
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['taskId', 'userId', 'projectId']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        task_id = data.get('taskId')
        user_id = data.get('userId')
        project_id = data.get('projectId')
        task_type = data.get('taskType', 'standard')
        estimated_hours = data.get('estimatedHours', 0)
        actual_hours = data.get('actualHours', 0)
        completed_at = data.get('completedAt', datetime.utcnow().isoformat())

        logger.info(f"Processing billing for completed task: {task_id}, user: {user_id}, project: {project_id}")

        # Calculate billing based on task properties
        billing_result = calculate_billing(task_type, estimated_hours, actual_hours)

        # Process the billing record
        billing_record = {
            "billingId": f"bill_{task_id}_{int(datetime.utcnow().timestamp())}",
            "taskId": task_id,
            "userId": user_id,
            "projectId": project_id,
            "taskType": task_type,
            "estimatedHours": estimated_hours,
            "actualHours": actual_hours,
            "rate": billing_result['rate'],
            "amount": billing_result['amount'],
            "currency": "USD",
            "processedAt": datetime.utcnow().isoformat(),
            "status": "calculated"
        }

        # In a real implementation, you would save this to a database
        # and potentially trigger payment processing
        logger.info(f"Billing calculated for task {task_id}: ${billing_record['amount']}")

        return jsonify({
            "status": "success",
            "billingRecord": billing_record,
            "message": f"Billing processed for task {task_id}"
        }), 200

    except Exception as e:
        logger.error(f"Error processing task completion: {str(e)}")
        return jsonify({"error": "Internal server error processing billing"}), 500

def calculate_billing(task_type, estimated_hours, actual_hours):
    """
    Calculate billing based on task type and hours
    """
    # Define rate structure
    rates = {
        'standard': 50.0,    # $50/hour for standard tasks
        'premium': 100.0,    # $100/hour for premium tasks
        'urgent': 150.0,     # $150/hour for urgent tasks
        'maintenance': 30.0  # $30/hour for maintenance tasks
    }

    # Get rate based on task type, default to standard
    rate = rates.get(task_type.lower(), rates['standard'])

    # Calculate amount based on actual hours worked
    amount = actual_hours * rate

    # Apply penalties if actual hours exceed estimated by more than 20%
    if actual_hours > estimated_hours * 1.2 and estimated_hours > 0:
        penalty_rate = 0.1  # 10% penalty
        penalty_amount = amount * penalty_rate
        amount += penalty_amount
        logger.info(f"Applied {penalty_rate*100}% penalty for exceeding estimated hours: +${penalty_amount}")

    return {
        "rate": rate,
        "amount": round(amount, 2)
    }

@app.route('/healthz', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "billing-service"}), 200

@app.route('/billing-history/<user_id>', methods=['GET'])
def get_billing_history(user_id):
    """Get billing history for a user"""
    # In a real implementation, this would query a database
    return jsonify({
        "userId": user_id,
        "billingHistory": [],
        "totalAmount": 0
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)