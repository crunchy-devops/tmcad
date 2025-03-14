# Utils 
##  Total lines of code
find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.html" \) -print0 | perl -n0E 'BEGIN { $count = 0 } open my $fh, "<", $_ or next; $count += scalar grep { $_ ne "" } <$fh>; END { say "Total lines of code: $count" }'