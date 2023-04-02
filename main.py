#!/usr/bin/env python3

import argparse

from scapy.all import IP, ICMP, sr

# A handler for command line options
def handle_options():

    parser = argparse.ArgumentParser(description="Placeholder : Programd Description")
    parser.add_argument('-v', '--version', type=str, help='version', required=False)
    parser.add_argument('-o', '--output', type=str, help='output file', required=False)
    parser.add_argument('-f', '--input', type=str, help='input file', required=False)

    args = parser.parse_args()
    return args

# Read input file. The file contains a list of IP addresses
def read_input_file(input_file):

    ip_list = []
    with open(input_file, 'r') as f:
        for line in f:
            ip_list.append(line.strip())

    return ip_list

def main(args):

    # Call read_input_file() to read the input file, if given input file option
    if args.input:
        ip_list : list = read_input_file(args.input)

    # Create ICMP packet
    icmp = IP(dst="google.com")/ICMP()

    # Send ICMP packet
    ans, unans = sr(icmp, timeout=2, verbose=2)

    # Display results
    if ans:
        print(ans.summary())
        for r in ans:
            r[1].show()

    else:
        print("No reply")

if __name__ == "__main__":
    # Handle command line options
    options = handle_options()
    main(options)