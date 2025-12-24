from db_helper import db
import json
import asyncio

async def main(query, params=None):
    async with db.get_connection() as conn:
        cursor = await conn.cursor()
        if params:
            await cursor.execute(query, params)
        else:
            await cursor.execute(query)
        results = await cursor.fetchall()
        
        # Convert Row objects to dictionaries
        results_dict = [dict(row) for row in results]
        
        print(f"\nFound {len(results_dict)} results:\n")
        print("=" * 80)
        
        # Print results in a readable format
        for i, row in enumerate(results_dict, 1):
            for key, value in row.items():
                # Truncate long values for readability
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                print(f"  {key}: {value}")
        
        print("\n" + "=" * 80)
        print(f"\nTotal: {len(results_dict)} rows")
        
        # Optionally print as JSON
        # print("\nJSON format:")
        # print(json.dumps(results_dict, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main("""SELECT * FROM compensation_data 
                WHERE tower = ? AND location = ?
                ORDER BY serial_no
                LIMIT ? """, ['application development', 'sweden', 500]))