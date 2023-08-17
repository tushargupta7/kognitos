import json
import boto3
from decimal import Decimal
from json import JSONEncoder

dynamodb = boto3.resource('dynamodb')
table_name = 'word_stats'
table = dynamodb.Table(table_name)


class DecimalEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def get_palindrome_count():
    try:
        response = table.scan(
            FilterExpression='isPalindrome = :val',
            ExpressionAttributeValues={':val': True}
        )

        palindrome_count = sum(item['occurrences'] for item in response['Items'])
        return palindrome_count
    except Exception as e:
        print("Error fetching palindrome count:", str(e))
        return 0

palindrome_count = get_palindrome_count()

def is_palindrome(s):
    return s == s[::-1]

def update_occurence_in_db(input_word, is_palindrome_word):
    try:
        response = table.update_item(
            Key={'word': input_word},
            UpdateExpression="SET occurrences = if_not_exists(occurrences, :zero) + :incr, isPalindrome = :palindrome",
            ExpressionAttributeValues={':zero': 0, ':incr': 1, ':palindrome': is_palindrome_word},
            ReturnValues="ALL_NEW"
        )
        return response
    except Exception as e:
        print("Error updating occurrence in DB:", str(e))
        return {}

def get_result(response, palindrome_count):
    return {
        "occurrences": response.get('Attributes', {}).get('occurrences', 0),
        "palindromes": palindrome_count
    }

def bad_request_response():
    return {
            "statusCode": 400,
            "body": json.dumps({"error":"Invalid Request"})
        }

def success_response(response,palindrome_count):
    return {
            "statusCode": 200,
            "body": json.dumps(get_result(response, palindrome_count), cls=DecimalEncoder)
        }

def lambda_handler(event, context):
    global palindrome_count  # Declare palindrome_count as global
    try:
        body = event['body']
        data = json.loads(body)
        input_word = data.get("word", "").lower()
        if not input_word:
            return bad_request_response()

        # Check if the input word is a palindrome
        is_palindrome_word = is_palindrome(input_word)

        # Update DynamoDB item
        response = update_occurence_in_db(input_word, is_palindrome_word)

        # Update palindrome_count
        if is_palindrome_word:
            palindrome_count += 1

        return success_response(response,palindrome_count)

    except Exception as e:
        print("Lambda execution error:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }
