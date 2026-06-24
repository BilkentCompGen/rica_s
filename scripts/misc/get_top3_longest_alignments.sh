grep -v "^#" $1 | sort -k1,1 -k4,4nr | awk -F'\t' '
{
    # If this is a new query, reset our counter
    if ($1 != current_query) {
        current_query = $1
        count = 0
    }
    
    # If we havent printed 3 hits for this query yet, print it and increase the counter
    if (count < 3) {
        print $0
        count++
    }
}' > $1_top3_longest_per_query.blastout
